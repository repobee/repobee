import random
import itertools
import pytest
from unittest.mock import MagicMock, PropertyMock, call

import github
import _repobee
import _repobee.ext
import _repobee.ext.github
from _repobee import util
from _repobee import exception
from repobee_plug import apimeta
from _repobee.ext.github import REQUIRED_OAUTH_SCOPES

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

CLOSE_ISSUE = apimeta.Issue(
    "close this issue", "This is a body", 3, random_date(), "slarse"
)
DONT_CLOSE_ISSUE = apimeta.Issue(
    "Don't close this issue", "Another body", 4, random_date(), "glassey"
)
OPEN_ISSUES = [CLOSE_ISSUE, DONT_CLOSE_ISSUE]

CLOSED_ISSUES = [
    apimeta.Issue(
        "This is a closed issue",
        "With an uninteresting body",
        1,
        random_date(),
        "tmore",
    ),
    apimeta.Issue(
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
def review_students():
    return ["ham", "spam", "bacon", "eggs"]


@pytest.fixture
def review_teams(review_students):
    master_repo = "week-1"
    review_teams = {}
    for i, student in enumerate(review_students):
        review_teams[util.generate_review_team_name(student, master_repo)] = (
            review_students[:i] + review_students[i + 1 :]
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
        return_value=REQUIRED_OAUTH_SCOPES
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
def repo_infos(teams_and_members, teams):
    descriptions = ["A nice repo for {}".format(team.name) for team in teams]
    repo_names = ["{}-week-2".format(team.name) for team in teams]
    return [
        apimeta.Repo(name, description, True, team.id)
        for name, description, team in zip(repo_names, descriptions, teams)
    ]


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
def repos(organization, no_repos, repo_infos):
    for ri in repo_infos:
        organization.create_repo(
            ri.name, ri.description, ri.private, ri.team_id
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
    return _repobee.ext.github.GitHubAPI(BASE_URL, TOKEN, ORG_NAME, USER)


class TestEnsureTeamsAndMembers:
    @staticmethod
    def assert_teams_equal(actual_teams, expected_teams):
        """Assert that the teams are equal, except for the implementation and
        id.
        """
        assert len(actual_teams) == len(expected_teams)
        for actual, expected in zip(
            sorted(actual_teams), sorted(expected_teams)
        ):
            assert (actual.name, sorted(actual.members)) == (
                expected.name,
                sorted(expected.members),
            )

    @pytest.fixture
    def team_wrappers(self, teams_and_members):
        """Wrap the teams_and_members dictionaries into apimeta.Team classes.

        TODO: Remove this when this test suite is rewritten.
        """
        return [
            apimeta.Team(name=team_name, members=members)
            for team_name, members in teams_and_members.items()
        ]

    def test_no_previous_teams(self, api, team_wrappers, no_teams):
        """Test that ensure_teams_and_members works as expected when there are
        no previous teams, and all users exist. This is a massive end-to-end
        test of the function with only the lower level API's mocked out.
        """
        expected_teams = list(team_wrappers)
        api.ensure_teams_and_members(expected_teams)
        self.assert_teams_equal(api.get_teams(), expected_teams)

    def test_all_teams_exist_but_without_members(
        self, api, team_wrappers, teams
    ):
        """Test that ensure_teams_and_members works as expected when all of
        the teams already exist, but have no members in them.
        """
        expected_teams = list(team_wrappers)
        api.ensure_teams_and_members(expected_teams)
        self.assert_teams_equal(api.get_teams(), expected_teams)

    @pytest.mark.parametrize(
        "unexpected_exc",
        [
            exception.APIError("", 404),
            exception.APIError("", 400),
            exception.APIError("", 500),
        ],
    )
    def test_raises_on_non_422_exception(
        self, api, organization, team_wrappers, unexpected_exc
    ):
        """Should raise if anything but a 422 http error is raised when
        creating the team.
        """

        def raise_(*args, **kwargs):
            raise unexpected_exc

        organization.create_team.side_effect = raise_

        with pytest.raises(exception.UnexpectedException):
            api.ensure_teams_and_members(team_wrappers)

    def test_running_twice_has_no_ill_effects(
        self, api, no_teams, team_wrappers
    ):
        """Tests that add_to_team is not called if all members are already
        in it."""
        expected_teams = list(team_wrappers)
        api.ensure_teams_and_members(expected_teams)
        api.ensure_teams_and_members(expected_teams)
        self.assert_teams_equal(api.get_teams(), expected_teams)


class TestCreateRepos:
    def test_creates_correct_repos(self, no_repos, repo_infos, api):
        """Assert that org.create_repo is called with the correct arguments."""
        # expect (self, repo_info) call args
        expected_calls = [
            call(
                info.name,
                description=info.description,
                private=info.private,
                team_id=info.team_id,
            )
            for info in repo_infos
        ]

        api.create_repos(repo_infos)

        assert repos
        api.org.create_repo.assert_has_calls(expected_calls)

    def test_skips_existing_repos(self, no_repos, repo_infos, api):
        """Assert that create_repo is called with all repos even when there are
        exceptions.
        """
        expected_calls = [
            call(
                info.name,
                description=info.description,
                private=info.private,
                team_id=info.team_id,
            )
            for info in repo_infos
        ]
        # create one repo in advance
        api.create_repos(repo_infos[:1])

        # start test
        api.create_repos(repo_infos)

        api.org.create_repo.assert_has_calls(expected_calls)

    @pytest.mark.parametrize(
        "unexpected_exception",
        (SERVER_ERROR, RuntimeError(), NOT_FOUND_EXCEPTION),
    )
    def test_raises_on_unexpected_error(
        self, no_repos, repo_infos, api, unexpected_exception
    ):
        create_repo_mock = api.org.create_repo
        side_effect = [create_repo_mock] * len(repo_infos)
        side_effect_github_exception = [unexpected_exception] + side_effect[1:]

        create_repo_mock.side_effect = side_effect_github_exception
        with pytest.raises(exception.APIError):
            api.create_repos(repo_infos)

    def test_returns_all_urls(self, mocker, repos, repo_infos, api):
        """Assert that create_repo returns the urls for all repos, even if there
        are validation errors.
        """
        expected_urls = [
            api._insert_auth(generate_repo_url(info.name, ORG_NAME))
            for info in repo_infos
        ]

        actual_urls = api.create_repos(repo_infos)
        assert actual_urls == expected_urls
        for url in actual_urls:
            assert TOKEN in url

    def test_create_repos_without_team_id(self, api):
        """If there is no team id specified for the repo, then
        github.Organization.create_repo must be called without the team_id
        argument (because if it is called with team_id=None, there is a crash).
        """
        repo = apimeta.Repo(
            name="repo",
            description="Some description",
            private=True,
            team_id=None,  # this is the important part!
        )

        api.create_repos([repo])

        api._org.create_repo.assert_called_once_with(
            repo.name, description=repo.description, private=repo.private
        )


class TestGetRepoUrls:
    """Tests for get_repo_urls."""

    def test_with_token_and_user(self, repos, api):
        repo_names = [repo.name for repo in repos]
        api._user = USER
        expected_urls = [api._insert_auth(repo.html_url) for repo in repos]

        urls = api.get_repo_urls(repo_names)

        assert sorted(urls) == sorted(expected_urls)
        for url in urls:
            assert "{}:{}".format(USER, TOKEN) in url

    def test_with_students(self, repos, api):
        """Test that supplying students causes student repo names to be
        generated as the Cartesian product of the supplied repo names and the
        students.
        """
        students = list(constants.STUDENTS)
        master_repo_names = [repo.name for repo in repos]
        expected_repo_names = util.generate_repo_names(
            students, master_repo_names
        )
        # assume works correctly when called with just repo names
        expected_urls = api.get_repo_urls(expected_repo_names)

        actual_urls = api.get_repo_urls(master_repo_names, teams=students)

        assert len(actual_urls) == len(students) * len(master_repo_names)
        assert sorted(expected_urls) == sorted(actual_urls)


class TestOpenIssue:
    """Tests for open_issue."""

    def test_on_existing_repos(self, api, repos, issues):
        repo_names = [repo.name for repo in repos]

        api.open_issue(ISSUE.title, ISSUE.body, repo_names)

        for repo in repos:
            repo.create_issue.assert_called_once_with(
                ISSUE.title, body=ISSUE.body
            )

    def test_on_some_non_existing_repos(self, api, repos):
        """Assert that repos that do not exist are simply skipped."""

        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ] + [repo.name for repo in repos]

        api.open_issue(ISSUE.title, ISSUE.body, repo_names)

        for repo in repos:
            repo.create_issue.assert_called_once_with(
                ISSUE.title, body=ISSUE.body
            )

    def test_no_crash_when_no_repos_are_found(self, api, repos, happy_github):
        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ]

        api.open_issue(ISSUE.title, ISSUE.body, repo_names)


class TestCloseIssue:
    """Tests for close_issue."""

    def test_closes_correct_issues(self, repos, issues, api):
        """Given repos with existing issues, assert that the corect issues are
        closed.
        """
        repo_names = [repo.name for repo in repos]
        expected_closed = [
            issue for issue in issues if issue.title == CLOSE_ISSUE.title
        ]
        expected_not_closed = [
            issue for issue in issues if issue.title == DONT_CLOSE_ISSUE.title
        ]
        assert expected_closed, "pre-test assert"
        assert expected_not_closed, "pre-test assert"
        regex = "^{}$".format(CLOSE_ISSUE.title)

        api.close_issue(regex, repo_names)

        for issue in expected_not_closed:
            assert not issue.edit.called
        for issue in expected_closed:
            # issue.edit.assert_called_once_with(state='closed')
            assert issue.edit.called

    def test_no_crash_if_no_repos_found(self, api, repos, issues):
        """Tests that there is no crash if no repos are found."""
        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ]

        regex = "^{}$".format(CLOSE_ISSUE.title)
        api.close_issue(regex, repo_names)

        for issue in issues:
            assert not issue.edit.called

    def test_no_crash_if_no_issues_found(self, api, repos, issues):
        """Tests that there is no crash if repos are found, but no matching
        issues.
        """
        repo_names = [repo.name for repo in repos]
        regex = "^{}$".format("non-matching-regex")

        api.close_issue(regex, repo_names)

        for issue in issues:
            assert not issue.edit.called


class TestGetIssues:
    """Tests for get_issues."""

    @staticmethod
    def assert_issues_equal(actual_issues, expected_issues):
        """The expected issues don't have the mocked implementation, while the
        actual issues all should have it.
        """
        actual_issues, expected_issues = (
            list(actual_issues),
            list(expected_issues),
        )
        assert len(actual_issues) == len(expected_issues)
        for act, exp in zip(sorted(actual_issues), sorted(expected_issues)):
            assert act.implementation
            for field_name in apimeta.Issue._fields:
                if field_name == "implementation":
                    continue
                assert getattr(act, field_name) == getattr(exp, field_name)

    def test_get_all_open_issues(self, repos, issues, api):
        repo_names = [repo.name for repo in repos]

        name_issues_pairs = api.get_issues(
            repo_names, state=apimeta.IssueState.OPEN
        )

        found_repos = []
        for repo_name, issue_gen in name_issues_pairs:
            found_repos.append(repo_name)

            self.assert_issues_equal(
                actual_issues=issue_gen, expected_issues=OPEN_ISSUES
            )

        assert sorted(found_repos) == sorted(repo_names)

    def test_get_all_closed_issues(self, repos, issues, api):
        repo_names = [repo.name for repo in repos]

        name_issues_pairs = api.get_issues(
            repo_names, state=apimeta.IssueState.CLOSED
        )

        found_repos = []
        for repo_name, issue_gen in name_issues_pairs:
            found_repos.append(repo_name)

            self.assert_issues_equal(
                actual_issues=issue_gen, expected_issues=CLOSED_ISSUES
            )

        assert sorted(found_repos) == sorted(repo_names)

    def test_get_issues_when_one_repo_doesnt_exist(self, repos, issues, api):
        """It should just ignore the repo that does not exist (and log the
        error)."""
        non_existing = "definitely-non-existing-repo"
        repo_names = [repo.name for repo in repos] + [non_existing]
        random.shuffle(repo_names)

        name_issues_pairs = api.get_issues(
            repo_names, state=apimeta.IssueState.OPEN
        )

        found_repos = []
        for repo_name, issue_gen in name_issues_pairs:
            found_repos.append(repo_name)

            self.assert_issues_equal(
                actual_issues=issue_gen, expected_issues=OPEN_ISSUES
            )

        assert len(found_repos) + 1 == len(repo_names)
        assert set(found_repos) == set(repo_names) - {non_existing}

    def test_get_open_issues_by_regex(self, repos, issues, api):
        """Should filter by regex."""
        sought_issue = OPEN_ISSUES[1]
        repo_names = [repo.name for repo in repos]
        regex = "^{}$".format(sought_issue.title)

        name_issues_pairs = api.get_issues(
            repo_names, state=apimeta.IssueState.OPEN, title_regex=regex
        )

        found_repos = []
        for repo_name, issue_gen in name_issues_pairs:
            found_repos.append(repo_name)

            self.assert_issues_equal(
                actual_issues=issue_gen, expected_issues=[sought_issue]
            )

        assert sorted(found_repos) == sorted(repo_names)


@pytest.fixture
def team_to_repos(api, no_repos, organization):
    """Create a team_to_repos mapping for use in _add_repos_to_teams, anc create
    each team and repo. Return the team_to_repos mapping.
    """
    num_teams = 10
    # arrange
    team_names = ["team-{}".format(i) for i in range(num_teams)]
    repo_names = ["some-repo-{}".format(i) for i in range(num_teams)]
    for name in team_names:
        organization.create_team(name, permission="pull")
    for name in repo_names:
        organization.create_repo(name)
    team_to_repos = {
        team_name: [repo_name]
        for team_name, repo_name in zip(team_names, repo_names)
    }
    return team_to_repos


class TestAddReposToReviewTeams:
    def test_with_default_issue(self, team_to_repos, organization, api):
        num_teams = len(team_to_repos)
        default_issue = _repobee.ext.github.DEFAULT_REVIEW_ISSUE
        assert num_teams, "pre-test assert"
        team_repo_tuples = [
            (team, *repos) for team, repos in team_to_repos.items()
        ]
        assert len(team_repo_tuples) == num_teams, "pre-test assert"

        api.add_repos_to_review_teams(team_to_repos, None)

        for team_name, repo_name in team_repo_tuples:
            team = organization.get_team(
                hash(team_name)
            )  # hash(team_name) is the id, see the fixture!
            repo = organization.get_repo(repo_name)
            assert team.add_to_repos.called_once_with(repo)

            repo.create_issue.assert_called_once_with(
                default_issue.title,
                body=default_issue.body,
                assignees=team.get_members(),
            )


class TestAddReposToTeams:
    def test_happy_path(self, team_to_repos, api):
        num_teams = len(team_to_repos)
        expected_tups = sorted(team_to_repos.items())

        # act
        result = list(api._add_repos_to_teams(team_to_repos))
        result.sort(key=lambda tup: tup[0].name)

        # assert
        assert len(result) == len(team_to_repos) == num_teams
        for res_tup, expected_tup in zip(result, expected_tups):
            expected_team_name, expected_repo_names = expected_tup
            expected_repo_name = expected_repo_names[0]

            actual_team, actual_repo = res_tup

            actual_team.add_to_repos.assert_called_once_with(actual_repo)
            assert actual_team.name == expected_team_name
            assert actual_repo.name == expected_repo_name


class TestDeleteTeams:
    def test_delete_non_existing_teams_does_not_crash(self, no_teams, api):
        team_names = ["week-{}".format(i) for i in range(10)]

        api.delete_teams(team_names)

    def test_delete_existing_teams(self, teams, api):
        team_names = [team.name for team in teams]

        api.delete_teams(team_names)

        assert all(map(lambda t: t.delete.called, teams))


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
        _repobee.ext.github.GitHubAPI.verify_settings(
            USER, ORG_NAME, BASE_URL, TOKEN
        )

    def test_empty_token_raises_bad_credentials(
        self, happy_github, monkeypatch, api
    ):
        with pytest.raises(exception.BadCredentials) as exc_info:
            _repobee.ext.github.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, ""
            )

        assert "token is empty" in str(exc_info.value)

    def test_incorrect_info_raises_not_found_error(self, github_bad_info, api):
        with pytest.raises(exception.NotFoundError):
            _repobee.ext.github.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )

    def test_bad_token_scope_raises(self, happy_github, api):
        type(happy_github).oauth_scopes = PropertyMock(return_value=["repo"])

        with pytest.raises(exception.BadCredentials) as exc_info:
            _repobee.ext.github.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )
        assert "missing one or more oauth scopes" in str(exc_info.value)

    def test_not_owner_raises(self, happy_github, organization, api):
        with pytest.raises(exception.BadCredentials) as exc_info:
            _repobee.ext.github.GitHubAPI.verify_settings(
                NOT_OWNER, ORG_NAME, BASE_URL, TOKEN
            )

        assert "user {} is not an owner".format(NOT_OWNER) in str(
            exc_info.value
        )

    def test_raises_unexpected_exception_on_unexpected_status(
        self, happy_github, api
    ):
        happy_github.get_user.side_effect = SERVER_ERROR
        with pytest.raises(exception.UnexpectedException):
            api.verify_settings(USER, ORG_NAME, BASE_URL, TOKEN)

    def test_none_user_raises(self, happy_github, organization, api):
        """If NamedUser.login is None, there should be an exception. Happens if
        you provide a URL that points to a GitHub instance, but not to the API
        endpoint.
        """
        happy_github.get_user.side_effect = lambda _: User(login=None)

        with pytest.raises(exception.UnexpectedException) as exc_info:
            _repobee.ext.github.GitHubAPI.verify_settings(
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

        with pytest.raises(exception.UnexpectedException) as exc_info:
            _repobee.ext.github.GitHubAPI.verify_settings(
                USER, ORG_NAME, BASE_URL, TOKEN
            )

        for msg in expected_messages:
            assert msg in str(exc_info.value)


class TestGetPeerReviewProgress:
    """Tests for get_peer_review_progress

    TODO: These tests need to be expanded. A lot.
    """

    def test_nothing_returns(self, review_students, review_teams, api):
        """Test calling the function when none of the functions return
        iterables.
        """
        review_team_names = list(review_teams.keys())
        api.get_review_progress(review_team_names, review_students, "peer")

    def test_with_review_teams_but_no_repos(
        self, review_students, review_teams, teams, api
    ):
        review_team_names = list(review_teams.keys())
        api.get_review_progress(review_team_names, review_students, "peer")
