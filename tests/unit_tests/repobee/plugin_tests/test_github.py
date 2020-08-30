import itertools
import pytest
from unittest.mock import MagicMock, PropertyMock, patch

import github

import repobee_plug as plug

import _repobee.ext.defaults.github as github_plugin
from _repobee.ext.defaults.github import REQUIRED_TOKEN_SCOPES

import constants
import functions

ORG_NAME = constants.ORG_NAME
ISSUE = constants.ISSUE
TOKEN = constants.TOKEN


class GithubException(Exception):
    def __init__(self, msg, status):
        super().__init__(msg)
        self.msg = msg
        self.status = status


NOT_FOUND_EXCEPTION = GithubException(msg=None, status=404)
VALIDATION_ERROR = GithubException(msg=None, status=422)
SERVER_ERROR = GithubException(msg=None, status=500)

USER = constants.USER
NOT_OWNER = "notanowner"
ORG_NAME = constants.ORG_NAME
BASE_URL = constants.BASE_URL
ISSUE = constants.ISSUE
TOKEN = constants.TOKEN

generate_repo_url = functions.generate_repo_url
random_date = functions.random_date
to_magic_mock_issue = functions.to_magic_mock_issue
from_magic_mock_issue = functions.from_magic_mock_issue

User = constants.User

CLOSE_ISSUE = plug.Issue(
    "close this issue", "This is a body", 3, random_date(), "slarse"
)
DONT_CLOSE_ISSUE = plug.Issue(
    "Don't close this issue", "Another body", 4, random_date(), "glassey"
)
OPEN_ISSUES = [CLOSE_ISSUE, DONT_CLOSE_ISSUE]

CLOSED_ISSUES = [
    plug.Issue(
        "This is a closed issue",
        "With an uninteresting body",
        1,
        random_date(),
        "tmore",
    ),
    plug.Issue(
        "Yet another closed issue",
        "Even less interesting body",
        2,
        random_date(),
        "viklu",
    ),
]


def raise_404(*args, **kwargs):
    raise GithubException("Couldn't find something", 404)


def raise_422(*args, **kwargs):
    raise GithubException("Already exists", 422)


def raise_401(*args, **kwargs):
    raise GithubException("Access denied", 401)


@pytest.fixture
def review_student_teams():
    return [
        plug.StudentTeam(members=[student])
        for student in ("ham", "spam", "bacon", "eggs")
    ]


@pytest.fixture(autouse=True)
def mock_github(mocker):
    return mocker.patch("github.Github", autospec=True)


@pytest.fixture
def review_teams(review_student_teams):
    master_repo = "week-1"
    review_teams = {}
    for i, student_team in enumerate(review_student_teams):
        review_teams[
            plug.generate_review_team_name(student_team, master_repo)
        ] = itertools.chain.from_iterable(
            team.members
            for team in review_student_teams[:i]
            + review_student_teams[i + 1 :]
        )
    return review_teams


@pytest.fixture
def teams_and_members(review_teams):
    """Fixture with a dictionary contain a few teams with member lists."""
    return {
        "one": ["first", "second"],
        "two": ["two"],
        "last_team": [str(i) for i in range(10)],
        **review_teams,
    }


@pytest.fixture
def happy_github(mocker, monkeypatch, teams_and_members):
    """mock of github.Github which raises no exceptions and returns the
    correct values.
    """
    github_instance = MagicMock()
    github_instance.get_user.side_effect = (
        lambda user: User(login=user)
        if user in [USER, NOT_OWNER]
        else raise_404()
    )
    type(github_instance).oauth_scopes = PropertyMock(
        return_value=REQUIRED_TOKEN_SCOPES
    )

    usernames = set(
        itertools.chain(*[members for _, members in teams_and_members.items()])
    )

    def get_user(username):
        if username in [*usernames, USER, NOT_OWNER]:
            user = MagicMock(spec=github.NamedUser.NamedUser)
            type(user).login = PropertyMock(return_value=username)
            return user
        else:
            raise_404()

    github_instance.get_user.side_effect = get_user
    monkeypatch.setattr(github, "GithubException", GithubException)
    mocker.patch(
        "github.Github",
        side_effect=lambda login_or_token, base_url: github_instance,
    )

    return github_instance


@pytest.fixture
def organization(happy_github):
    """Attaches an Organization mock to github.Github.get_organization, and
    returns the mock.
    """
    organization = MagicMock()
    organization.get_members = lambda role: [
        User(login="blablabla"),
        User(login="hello"),
        User(login=USER),
    ]
    type(organization).html_url = PropertyMock(
        return_value=generate_repo_url("", ORG_NAME).rstrip("/")
    )
    happy_github.get_organization.side_effect = (
        lambda org_name: organization if org_name == ORG_NAME else raise_404()
    )
    return organization


def mock_team(name):
    """create a mock team that tracks its members."""
    team = MagicMock()
    members = set()
    team.get_members.side_effect = lambda: list(members)
    team.add_membership.side_effect = lambda user: members.add(user)
    type(team).name = PropertyMock(return_value=name)
    type(team).id = PropertyMock(return_value=hash(name))
    return team


@pytest.fixture
def no_teams(organization):
    """A fixture that sets up the teams functionality without adding any
    teams.
    """
    ids_to_teams = {}
    organization.get_team.side_effect = (
        lambda team_id: ids_to_teams[team_id]
        if team_id in ids_to_teams
        else raise_404()
    )
    organization.get_teams.side_effect = lambda: list(teams_)
    teams_ = []

    def create_team(name, permission):
        nonlocal teams_, ids_to_teams

        assert permission in ["push", "pull"]
        if name in [team.name for team in teams_]:
            raise_422()

        team = mock_team(name)
        ids_to_teams[team.id] = team
        teams_.append(team)
        return team

    organization.create_team.side_effect = create_team
    return teams_


@pytest.fixture
def teams(organization, no_teams, teams_and_members):
    """A fixture that returns a list of teams, which are all returned by the
    github.Organization.Organization.get_teams function."""
    team_names = teams_and_members.keys()
    for name in team_names:
        organization.create_team(name, permission="push")
    return no_teams  # the list of teams!


def mock_repo(name, description, private, team_id):
    repo = MagicMock()
    type(repo).name = PropertyMock(return_value=name)
    type(repo).description = PropertyMock(
        return_value="description of {}".format(name)
    )
    type(repo).html_url = PropertyMock(
        return_value=generate_repo_url(name, ORG_NAME)
    )
    # repo.get_teams.side_effect = lambda: [team]
    return repo


@pytest.fixture
def no_repos(teams_and_members, teams, organization):
    repos_in_org = {}

    def get_repo(repo_name):
        if repo_name in repos_in_org:
            return repos_in_org[repo_name]
        raise NOT_FOUND_EXCEPTION

    def create_repo(name, description="", private=True, team_id=None):
        nonlocal repos_in_org
        if name in repos_in_org:
            raise VALIDATION_ERROR
        repo = mock_repo(name, description, private, team_id)
        repos_in_org[name] = repo
        return repo

    organization.create_repo.side_effect = create_repo
    organization.get_repo.side_effect = get_repo
    organization.get_repos.side_effect = lambda: list(repos_in_org.values())


@pytest.fixture
def repos(organization, no_repos, teams_and_members, teams):
    for team in teams:
        organization.create_repo(
            f"{team.name}-week-2",
            description=f"A nice repo for {team.name}",
            private=True,
        )
    return organization.get_repos()


@pytest.fixture
def issues(repos):
    """Adds two issues to all repos such that Repo.get_issues returns the
    issues. One issue is expected to be closed and has title CLOSE_ISSUE.title
    and is marked with, while the other is expected not to be closed and has
    title DONT_CLOSE_ISSUE.title.
    """

    def attach_issues(repo):
        # for some reason, putting this inline in the loop caused every single
        # repo to get the SAME mocks returned by the lambda
        open_issue_mocks = [
            to_magic_mock_issue(issue) for issue in OPEN_ISSUES
        ]
        closed_issue_mocks = [
            to_magic_mock_issue(issue) for issue in CLOSED_ISSUES
        ]
        repo.get_issues.side_effect = (
            lambda state: open_issue_mocks
            if state == "open"
            else closed_issue_mocks
        )
        return open_issue_mocks + closed_issue_mocks

    issues = []
    for repo in repos:
        issues.extend(attach_issues(repo))

    return issues


@pytest.fixture(scope="function")
def api(happy_github, organization, no_teams):
    return github_plugin.GitHubAPI(BASE_URL, TOKEN, ORG_NAME, USER)


class TestInit:
    def test_raises_on_empty_user_arg(self):
        with pytest.raises(TypeError) as exc_info:
            github_plugin.GitHubAPI(BASE_URL, TOKEN, ORG_NAME, "")

        assert "argument 'user' must not be empty" in str(exc_info.value)

    @pytest.mark.parametrize("url", ["https://github.com", constants.HOST_URL])
    def test_raises_when_url_is_bad(self, url):
        with pytest.raises(plug.PlugError) as exc_info:
            github_plugin.GitHubAPI(url, TOKEN, ORG_NAME, USER)

        assert (
            "invalid base url, should either be https://api.github.com or "
            "end with '/api/v3'" in str(exc_info.value)
        )

    @pytest.mark.parametrize(
        "url", ["https://api.github.com", constants.BASE_URL]
    )
    def test_accepts_valid_urls(self, url):
        api = github_plugin.GitHubAPI(url, TOKEN, ORG_NAME, USER)

        assert isinstance(api, plug.PlatformAPI)


class TestInsertAuth:
    """Tests for insert_auth."""

    def test_inserts_into_https_url(self, api):
        url = f"{BASE_URL}/some/repo"
        authed_url = api.insert_auth(url)
        assert authed_url.startswith(f"https://{USER}:{TOKEN}")

    def test_raises_on_non_platform_url(self, api):
        url = "https://somedomain.com"

        with pytest.raises(plug.InvalidURL) as exc_info:
            api.insert_auth(url)

        assert "url not found on platform" in str(exc_info.value)


class TestGetRepoUrls:
    """Tests for get_repo_urls."""

    def test_with_token_and_user(self, repos, api):
        repo_names = [repo.name for repo in repos]
        api._user = USER
        expected_urls = [api.insert_auth(repo.html_url) for repo in repos]

        urls = api.get_repo_urls(repo_names, insert_auth=True)

        assert sorted(urls) == sorted(expected_urls)
        for url in urls:
            assert "{}:{}".format(USER, TOKEN) in url

    def test_with_students(self, repos, api):
        """Test that supplying students causes student repo names to be
        generated as the Cartesian product of the supplied repo names and the
        students.
        """
        students = list(constants.STUDENTS)
        assignment_names = [repo.name for repo in repos]
        expected_repo_names = plug.generate_repo_names(
            students, assignment_names
        )
        # assume works correctly when called with just repo names
        expected_urls = api.get_repo_urls(expected_repo_names)

        actual_urls = api.get_repo_urls(
            assignment_names, team_names=[t.name for t in students]
        )

        assert len(actual_urls) == len(students) * len(assignment_names)
        assert sorted(expected_urls) == sorted(actual_urls)


@pytest.fixture(params=["get_user", "get_organization"])
def github_bad_info(request, api, happy_github):
    """Fixture with a github instance that raises GithubException 404 when
    use the user, base_url and org_name arguments to .
    """
    getattr(happy_github, request.param).side_effect = raise_404
    return happy_github


class TestVerifySettings:
    """Tests for the verify_settings function."""

    def test_happy_path(self, happy_github, organization, api):
        """Tests that no exceptions are raised when all info is correct."""
        github_plugin.GitHubAPI.verify_settings(
            USER, ORG_NAME, BASE_URL, TOKEN
        )

    def test_empty_token_raises_bad_credentials(
        self, happy_github, monkeypatch, api
    ):
        with pytest.raises(plug.BadCredentials) as exc_info:
            github_plugin.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, ""
            )

        assert "token is empty" in str(exc_info.value)

    def test_incorrect_info_raises_not_found_error(self, github_bad_info, api):
        with pytest.raises(plug.NotFoundError):
            github_plugin.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )

    def test_bad_token_scope_raises(self, happy_github, api):
        type(happy_github).oauth_scopes = PropertyMock(return_value=["repo"])

        with pytest.raises(plug.BadCredentials) as exc_info:
            github_plugin.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )
        assert "missing one or more access token scopes" in str(exc_info.value)

    def test_not_owner_raises(self, happy_github, organization, api):
        with pytest.raises(plug.BadCredentials) as exc_info:
            github_plugin.GitHubAPI.verify_settings(
                NOT_OWNER, ORG_NAME, BASE_URL, TOKEN
            )

        assert "user {} is not an owner".format(NOT_OWNER) in str(
            exc_info.value
        )

    def test_raises_unexpected_exception_on_unexpected_status(
        self, happy_github, api
    ):
        happy_github.get_user.side_effect = SERVER_ERROR
        with pytest.raises(plug.UnexpectedException):
            api.verify_settings(USER, ORG_NAME, BASE_URL, TOKEN)

    def test_none_user_raises(self, happy_github, organization, api):
        """If NamedUser.login is None, there should be an exception. Happens if
        you provide a URL that points to a GitHub instance, but not to the API
        endpoint.
        """
        happy_github.get_user.side_effect = lambda _: User(login=None)

        with pytest.raises(plug.UnexpectedException) as exc_info:
            github_plugin.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )

        assert "Possible reasons: bad api url" in str(exc_info.value)

    def test_mismatching_user_login_raises(
        self, happy_github, organization, api
    ):
        """I'm not sure if this can happen, but since the None-user thing
        happened, better safe than sorry.
        """
        wrong_username = USER + "other"
        happy_github.get_user.side_effect = lambda username: User(
            username + "other"
        )
        expected_messages = [
            "Specified login is {}, but the fetched user's login is {}".format(
                USER, wrong_username
            ),
            "Possible reasons: unknown",
        ]

        with pytest.raises(plug.UnexpectedException) as exc_info:
            github_plugin.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )

        for msg in expected_messages:
            assert msg in str(exc_info.value)


class TestGetRepoIssues:
    """Tests for the get_repo_issues function."""

    def test_fetches_all_issues(self, happy_github, api):
        impl_mock = MagicMock(spec=github.Repository.Repository)
        repo = plug.Repo(
            name="name",
            description="descr",
            private=True,
            url="bla",
            implementation=impl_mock,
        )

        api.get_repo_issues(repo)

        impl_mock.get_issues.assert_called_once_with(state="all")


class TestCreateIssue:
    """Tests for the create_issue function."""

    def test_sets_assignees_defaults_to_notset(self, happy_github, api):
        """Assert that ``assignees = None`` is replaced with ``NotSet``."""
        impl_mock = MagicMock(spec=github.Repository.Repository)
        repo = plug.Repo(
            name="name",
            description="descr",
            private=True,
            url="bla",
            implementation=impl_mock,
        )

        with patch(
            "_repobee.ext.defaults.github.GitHubAPI._wrap_issue", autospec=True
        ):
            api.create_issue("Title", "Body", repo)

        impl_mock.create_issue.assert_called_once_with(
            "Title", body="Body", assignees=github.GithubObject.NotSet
        )
