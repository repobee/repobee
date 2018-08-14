import socket
from unittest.mock import MagicMock, PropertyMock, patch, call
from collections import namedtuple
import pytest
import github

from gits_pet.abstract_api_wrapper import REQUIRED_OAUTH_SCOPES
from gits_pet import pygithub_wrapper
from gits_pet import git
from gits_pet import exception
from gits_pet import tuples

USER = pytest.constants.USER
NOT_OWNER = 'notanowner'
ORG_NAME = pytest.constants.ORG_NAME
GITHUB_BASE_URL = pytest.constants.GITHUB_BASE_URL
ISSUE = pytest.constants.ISSUE

# titles are purposefully similar
CLOSE_ISSUE = tuples.Issue('close this issue', 'This is a body')
DONT_CLOSE_ISSUE = tuples.Issue("Don't close this issue", 'Another body')

GENERATE_REPO_URL = pytest.functions.GENERATE_REPO_URL
raise_ = pytest.functions.raise_

User = namedtuple('User', ('login', ))


class GithubException(Exception):
    def __init__(self, msg, status):
        self.msg = msg
        self.status = status


def raise_404(*args, **kwargs):
    raise GithubException("Couldn't find something", 404)


def raise_422(*args, **kwargs):
    raise GithubException("Already exists", 422)


def raise_401(*args, **kwargs):
    raise GithubException("Access denied", 401)


@pytest.fixture
def happy_github(mocker, monkeypatch):
    """mock of github.Github which raises no exceptions and returns the
    correct values.
    """
    github_instance = MagicMock()
    github_instance.get_user.side_effect = \
        lambda user: User(login=user) if user in [USER, NOT_OWNER] else raise_404()
    type(github_instance).oauth_scopes = PropertyMock(
        return_value=REQUIRED_OAUTH_SCOPES)

    monkeypatch.setattr(github, 'GithubException', GithubException)
    mocker.patch(
        'github.Github',
        side_effect=lambda login_or_token, base_url: github_instance)

    return github_instance


@pytest.fixture
def organization(happy_github):
    """Attaches an Organization mock to github.Github.get_organization, and
    returns the mock.
    """
    organization = MagicMock()
    organization.get_members = lambda role: \
        [User(login='blablabla'), User(login='hello'), User(login=USER)]
    type(organization).html_url = PropertyMock(
        return_value=GENERATE_REPO_URL('').rstrip('/'))
    happy_github.get_organization.side_effect = \
        lambda org_name: organization if org_name == ORG_NAME else raise_404()
    return organization


@pytest.fixture(params=['get_user', 'get_organization'])
def github_bad_info(request, happy_github):
    """Fixture with a github instance that raises GithubException 404 when
    use the user, base_url and org_name arguments to .
    """
    getattr(happy_github, request.param).side_effect = raise_404


@pytest.fixture
def users(happy_github):
    """A fixture that returns users that are attached to Github.get_user"""
    users = ('some-guy', 'slarse', 'glassey', 'other', 'more',
             *["generic-user-{}".format(i) for i in range(10)])
    happy_github.get_user.side_effect = lambda username: \
        username if username in users else raise_404()
    return list(users)


@pytest.fixture
def teams(organization):
    """A fixture that returns a list of teams, which are all returned by the
    github.Organization.Organization.get_teams function."""
    team_names = ('best team', 'another-team', 'second-last-team', 'last',
                  *["team-{}".format(i) for i in range(10)])
    teams = []
    ids_to_teams = {}
    for name in team_names:
        team = MagicMock()
        members = set()
        team.get_members.side_effect = lambda: list(members)
        team.add_membership.side_effect = lambda user: members.add(user)
        type(team).name = PropertyMock(return_value=name)
        type(team).id = PropertyMock(return_value=hash(name))
        ids_to_teams[team.id] = team
        teams.append(team)

    assert teams

    organization.get_team.side_effect = lambda team_id: \
        ids_to_teams[team_id] if team_id in ids_to_teams else raise_404()
    organization.get_teams.side_effect = lambda: list(teams)
    organization.create_team.side_effect = lambda team_name, permission: \
        raise_422() if team_name in team_names else None
    return teams


@pytest.fixture
def repos(organization, teams):
    repos = []
    for team in teams:
        name = "{}-repo".format(team.name)
        repo = MagicMock()
        type(repo).name = PropertyMock(return_value=name)
        type(repo).description = PropertyMock(
            return_value="description of {}".format(name))
        type(repo).html_url = PropertyMock(
            return_value=GENERATE_REPO_URL(name))
        repo.get_teams.side_effect = lambda: [team]
        repos.append(repo)

    def get_repo(repo_name):
        matches = [repo for repo in repos if repo.name == repo_name]
        if not matches:
            raise_404()
        return matches[0]

    organization.get_repos.side_effect = lambda: list(repos)
    organization.get_repo.side_effect = get_repo
    return repos


def repo_mock_to_tuple(repo_mock):
    return tuples.Repo(
        name=repo_mock.name,
        description=repo_mock.description,
        private=repo_mock.private,
        team_id=repo_mock.team_id)


@pytest.fixture
def wrapper(happy_github):
    return pygithub_wrapper.PyGithubWrapper(GITHUB_BASE_URL, git.OAUTH_TOKEN,
                                            ORG_NAME)


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
        close_issue = MagicMock()
        close_issue.title = CLOSE_ISSUE.title
        close_issue.body = CLOSE_ISSUE.body
        dont_close_issue = MagicMock()
        dont_close_issue.title = DONT_CLOSE_ISSUE.title
        dont_close_issue.body = DONT_CLOSE_ISSUE.body
        repo.get_issues.side_effect = lambda state: [dont_close_issue, close_issue] if state == 'open' else []
        return close_issue, dont_close_issue

    issues = []
    for repo in repos:
        issues.extend(attach_issues(repo))

    return issues


class TestVerifyConnection:
    """Tests for the verify_connection function."""

    def test_happy_path(self, happy_github, organization):
        """Tests that no exceptions are raised when all info is correct."""
        pygithub_wrapper.PyGithubWrapper.verify_connection(
            USER, ORG_NAME, git.OAUTH_TOKEN, GITHUB_BASE_URL)

    def test_incorrect_info_raises_not_found_error(self, github_bad_info):
        with pytest.raises(exception.NotFoundError) as exc_info:
            pygithub_wrapper.PyGithubWrapper.verify_connection(
                USER, ORG_NAME, git.OAUTH_TOKEN, GITHUB_BASE_URL)

    def test_bad_token_scope_raises(self, happy_github):
        type(happy_github).oauth_scopes = PropertyMock(return_value=['repo'])

        with pytest.raises(exception.BadCredentials) as exc_info:
            pygithub_wrapper.PyGithubWrapper.verify_connection(
                USER, ORG_NAME, git.OAUTH_TOKEN, GITHUB_BASE_URL)
        assert "missing one or more oauth scopes" in str(exc_info)

    def test_not_owner_raises(self, happy_github, organization):
        with pytest.raises(exception.BadCredentials) as exc_info:
            pygithub_wrapper.PyGithubWrapper.verify_connection(
                NOT_OWNER, ORG_NAME, git.OAUTH_TOKEN, GITHUB_BASE_URL)

        assert "user {} is not an owner".format(NOT_OWNER) in str(exc_info)

    def test_raises_unexpected_exception_on_unexpected_status(
            self, happy_github, wrapper):
        happy_github.get_user.side_effect = raise_(
            GithubException("internal server error", 500))
        with pytest.raises(exception.UnexpectedException) as exc_info:
            wrapper.verify_connection(USER, ORG_NAME, git.OAUTH_TOKEN,
                                      GITHUB_BASE_URL)


def team_mock_to_tuple(team_mock):
    """Note that the members will go out-of-date if the team_mock is updated
    after conversion!
    """
    return tuples.Team(
        name=team_mock.name,
        members=list(team_mock.get_members()),
        id=team_mock.id)


class TestInit:
    """Test initializing PyGithubWrapper objects."""

    def test_init_with_bad_token_raises(self, happy_github):
        happy_github.get_organization.side_effect = raise_(
            GithubException("bad credentials", 401))

        with pytest.raises(exception.BadCredentials):
            wrapper = pygithub_wrapper.PyGithubWrapper(GITHUB_BASE_URL,
                                                       "some-token", ORG_NAME)

    def test_init_with_bad_url_raises(self, happy_github):
        happy_github.get_organization.side_effect = raise_(socket.gaierror())

        with pytest.raises(exception.ServiceNotFoundError):
            wrapper = pygithub_wrapper.PyGithubWrapper(
                GITHUB_BASE_URL, git.OAUTH_TOKEN, ORG_NAME)

    def test_init_raises_on_unexpected_exception(self, happy_github):
        happy_github.get_organization.side_effect = raise_(ValueError())

        with pytest.raises(exception.UnexpectedException):
            wrapper = pygithub_wrapper.PyGithubWrapper(
                GITHUB_BASE_URL, git.OAUTH_TOKEN, ORG_NAME)


class TestCreateRepo:
    """Tests for create_repo."""

    def test_happy_path(self, organization, wrapper, repos):
        repo = repo_mock_to_tuple(repos[0])
        assert wrapper._org == organization

        wrapper.create_repo(repo)

        organization.create_repo.assert_called_once_with(
            repo.name,
            description=repo.description,
            private=repo.private,
            team_id=repo.team_id)


class TestGetTeams:
    """Tests for get_teams and get_teams_in."""

    def test_get_teams(self, teams, wrapper):
        expected_teams = [team_mock_to_tuple(team) for team in teams]
        actual_teams = wrapper.get_teams()

        assert sorted(actual_teams) == sorted(expected_teams)

    def test_get_teams_in(self, teams, wrapper):
        expected_teams = [team_mock_to_tuple(team) for team in teams[2:-4]]
        team_names = [team.name for team in expected_teams]

        actual_teams = wrapper.get_teams_in(team_names)

        assert sorted(actual_teams) == sorted(expected_teams)


class TestAddToTeam:
    """Tests for add_to_team."""

    def test_raises_on_unexpeced_exception_from_get_users(
            self, happy_github, users, teams, wrapper):
        happy_github.get_user.side_effect = raise_(
            GithubException("Bad credentials", 401))

        with pytest.raises(exception.UnexpectedException):
            wrapper.add_to_team(users, team_mock_to_tuple(teams[0]))

    def test_add_with_no_previous_members(
            self, happy_github, users, teams, wrapper):
        """Test adding members to a team which has no members."""
        new_members = users[:3]
        team = teams[4]
        expected_calls = [call(user) for user in new_members]

        wrapper.add_to_team(new_members, team_mock_to_tuple(team))

        team.add_membership.assert_has_calls(expected_calls)

    def test_add_with_some_preexisting_members(self, 
                                               users, teams, wrapper):
        """Test adding members when some of the members have already been
        added. All calls should still be placed, as adding membership when it
        is already in place does nothing.
        """
        team = teams[7]
        previous_members = users[3:5]
        for member in previous_members:
            team.add_membership(member)
        assert sorted(
            team.get_members()) == sorted(previous_members), "pre-test assert"
        new_members = users[7:]
        all_members = previous_members + new_members
        expected_calls = [call(user) for user in all_members]

        wrapper.add_to_team(all_members, team_mock_to_tuple(team))

        team.add_membership.assert_has_calls(expected_calls)

    def test_add_with_some_non_existing_users(self, 
                                              users, teams, wrapper):
        existing_users = users[4:8]
        non_existing_users = ['do-not-exist-{}'.format(i) for i in range(3)]
        new_members = non_existing_users + existing_users
        team = teams[9]
        assert new_members, "pre-test assert"
        expected_calls = [call(user) for user in existing_users]

        wrapper.add_to_team(new_members, team_mock_to_tuple(team))

        team.add_membership.assert_has_calls(expected_calls)


def test_create_team_default_permission(happy_github, organization,
                                        wrapper):
    team_name = 'slarse'

    wrapper.create_team(team_name)

    organization.create_team.assert_called_once_with(
        team_name, permission='push')


def test_create_team_pull_permission(happy_github, organization,
                                     wrapper):
    team_name = 'herro'
    permission = 'pull'

    wrapper.create_team(team_name, permission=permission)

    organization.create_team.assert_called_once_with(
        team_name, permission=permission)


class TestOpenIssueIn:
    """Tests for open_issue_in."""

    def test_on_existing_repos(self, repos, wrapper):
        repo_names = [repo.name for repo in repos]

        wrapper.open_issue_in(ISSUE, repo_names)

        for repo in repos:
            repo.create_issue.assert_called_once_with(
                ISSUE.title, body=ISSUE.body)

    def test_on_some_non_existing_repos(self, repos, wrapper):
        """Assert that repos that do not exist are simply skipped."""

        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ] + [repo.name for repo in repos]

        wrapper.open_issue_in(ISSUE, repo_names)

        for repo in repos:
            repo.create_issue.assert_called_once_with(
                ISSUE.title, body=ISSUE.body)

    def test_no_crash_when_no_repos_are_found(self, repos, happy_github,
                                              wrapper):
        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ]

        wrapper.open_issue_in(ISSUE, repo_names)


class TestCloseIssuesIn:
    """Tests for close_issues_in."""

    def test_closes_correct_issues(self, repos, issues, wrapper):
        """Given repos with existing issues, assert that the corect issues are closed."""
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

        wrapper.close_issue_in(regex, repo_names)

        for issue in expected_not_closed:
            assert not issue.edit.called
        for issue in expected_closed:
            #issue.edit.assert_called_once_with(state='closed')
            assert issue.edit.called

    def test_no_crash_if_no_repos_found(self, repos, issues, wrapper):
        """Tests that there is no crash if no repos are found."""
        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ]

        regex = "^{}$".format(CLOSE_ISSUE.title)
        wrapper.close_issue_in(regex, repo_names)

        for issue in issues:
            assert not issue.edit.called

    def test_no_crash_if_no_issues_found(self, repos, issues, wrapper):
        """Tests that there is no crash if repos are found, but no matching issues."""
        repo_names = [repo.name for repo in repos]
        regex = "^{}$".format("non-matching-regex")

        wrapper.close_issue_in(regex, repo_names)

        for issue in issues:
            assert not issue.edit.called


class TestGetRepoUrl:
    """Tests for get_repo_url."""

    def test_on_existing_repos(self, repos, wrapper):
        repo_names = [repo.name for repo in repos]
        expected_urls = [repo.html_url for repo in repos]

        actual_urls = [wrapper.get_repo_url(name) for name in repo_names]

        assert actual_urls == expected_urls

    def test_raises_on_non_existing_repo(self, repos, wrapper):
        with pytest.raises(exception.NotFoundError):
            wrapper.get_repo_url('does-not-exist')


class TestCreateTeam:
    """Tests for create_team."""

    def test_create_team_default_permission(self, teams, wrapper,
                                            organization):
        team_name = "does-not-exist"

        wrapper.create_team(team_name)

        organization.create_team.assert_called_once_with(
            team_name, permission='push')

    def test_create_team_pull_permission(self, teams, wrapper, organization):
        team_name = "does-not-exist"
        permission = 'pull'

        wrapper.create_team(team_name, permission)

        organization.create_team.assert_called_once_with(
            team_name, permission=permission)

    def test_create_team_that_already_exists_raises_422(self, teams, wrapper):
        with pytest.raises(exception.GitHubError) as exc_info:
            wrapper.create_team(teams[0].name)

        assert exc_info.value.status == 422


@pytest.fixture
def repo_tuples(repos):
    repo_tups = [
        tuples.Repo(
            name=repo.name,
            description=repo.description,
            private=repo.private,
            team_id=repo.get_teams()[0].id,
            url=repo.html_url) for repo in repos
    ]
    assert repo_tups, "pre-test assert"
    return repo_tups


class TestGetRepos:
    """Tests for get_repos."""

    def test_get_all_repos(self, repos, repo_tuples, wrapper):
        """Test that all repos are returned if no team names are specified."""
        actual_repos = list(wrapper.get_repos())

        assert actual_repos == repo_tuples

    def test_get_some_repos(self, repos, repo_tuples, wrapper):
        expected_repos = repo_tuples[3:8]
        repo_names = [r.name for r in expected_repos]

        actual_repos = list(wrapper.get_repos(repo_names))

        assert actual_repos == expected_repos

    def test_empty_generator_when_no_matching_name(self, repos, wrapper):
        repo_names = [
            "repo-that-does-not-exist-{}".format(i) for i in range(10)
        ]

        actual_repos = list(wrapper.get_repos(repo_names))

        assert not actual_repos

    def test_get_repos_works_when_repo_has_no_team(self, repos, repo_tuples,
                                                   wrapper):
        repo = repos[3]
        repo.get_teams.side_effect = lambda: []
        repo_tuples[3] = tuples.Repo(
            name=repo.name,
            description=repo.description,
            private=repo.private,
            team_id=None,
            url=repo.html_url)

        actual_repos = list(wrapper.get_repos())

        assert actual_repos == repo_tuples


def test_org_url(organization, wrapper):
    org_url = wrapper.org_url

    assert org_url == "{}/{}".format(pytest.constants.HOST_URL,
                                     pytest.constants.ORG_NAME)
