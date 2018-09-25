import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from collections import namedtuple

import github
from repomate import github_api
from repomate import exception
from repomate import tuples

ORG_NAME = pytest.constants.ORG_NAME
ISSUE = pytest.constants.ISSUE

NOT_FOUND_EXCEPTION = exception.NotFoundError(msg=None, status=404)
VALIDATION_ERROR = exception.GitHubError(msg=None, status=422)
SERVER_ERROR = exception.GitHubError(msg=None, status=500)

GENERATE_REPO_URL = pytest.functions.GENERATE_REPO_URL


@pytest.fixture(scope='function')
def repos():
    team_names = ('team-one', 'team-two', 'team-three', 'team-four')
    descriptions = ["A nice repo for {}".format(tn) for tn in team_names]
    repo_names = ["{}-week-2".format(tn) for tn in team_names]
    privacy = (True, True, False, True)
    team_id = (1, 2, 3, 55)
    return [
        tuples.Repo(
            name, description, private, team_id, url=GENERATE_REPO_URL(name))
        for name, description, private, team_id in zip(
            repo_names, descriptions, privacy, team_id)
    ]


@pytest.fixture
def existing_teams():
    existing_teams = {}
    yield existing_teams


@pytest.fixture
def api_wrapper_mock(mocker, existing_teams, repos):
    api_wrapper_instance = MagicMock()

    # have create_team and get_teams work on a mocked dictionary
    api_wrapper_instance.create_repo.side_effect = \
        lambda repo_info: GENERATE_REPO_URL(repo_info.name)
    api_wrapper_instance.create_team.side_effect = \
        lambda team_name, permission: existing_teams.update({team_name: []})

    api_wrapper_instance.get_teams.side_effect = \
        lambda: [tuples.Team(name=name, members=members, id=hash(name)) for name, members in existing_teams.items()]

    api_wrapper_instance.get_teams_in.side_effect = \
        lambda team_names: list(set(team_names).intersection(existing_teams.keys()))

    # empty repo name and remove trailing slash
    type(api_wrapper_instance).org_url = PropertyMock(
        return_value=GENERATE_REPO_URL("").rstrip("/"))

    def add_to_team(members, team):
        for user in members:
            if user in existing_teams[team.name]:
                raise exception.GitHubError(
                    "{} already in {}".format(user, team.name), 422)
            existing_teams[team.name].append(user)

    api_wrapper_instance.add_to_team.side_effect = add_to_team

    api_wrapper_instance.get_user.side_effect = lambda username: username

    api_wrapper_instance.get_repo_url.side_effect = \
        lambda repo_name: GENERATE_REPO_URL(repo_name)

    api_wrapper_instance.get_repos.side_effect = \
        lambda repo_names: [repo for repo in repos if repo.name in repo_names]

    api_wrapper_mock = mocker.patch(
        'repomate.github_api.APIWrapper', return_value=api_wrapper_instance)

    return api_wrapper_instance


@pytest.fixture
def teams_and_members():
    """Fixture with a dictionary contain a few teams with member lists."""
    return {
        'team_one': ['first', 'second'],
        'two': ['two'],
        'last_team': [str(i) for i in range(10)]
    }


@pytest.fixture
def existing_teams_prefilled(existing_teams, teams_and_members):
    """Fixture with all of the teams (and members) in the teams_and_members
    fixture added to the existing teams. Note that the members are copied,
    so it's not the same sets.
    """
    for team_name, members in teams_and_members.items():
        existing_teams[team_name] = list(members)  # copy
        assert id(existing_teams[team_name]) != id(
            teams_and_members[team_name])
    assert existing_teams == teams_and_members

    return existing_teams


@pytest.fixture(scope='function')
def api(api_wrapper_mock, mocker):
    return github_api.GitHubAPI('bla', 'blue', 'bli')


class TestEnsureTeamsAndMembers:
    def test_no_previous_teams(self, api_wrapper_mock, existing_teams, api,
                               teams_and_members):
        """Test that ensure_teams_and_members works as expected when there are no
        previous teams, and all users exist. This is a massive end-to-end test of
        the function with only the lower level API's mocked out.
        """
        api.ensure_teams_and_members(teams_and_members)

        assert existing_teams == teams_and_members

    def test_all_teams_exist_but_without_members(
            self, api_wrapper_mock, existing_teams, api, teams_and_members):
        """Test that ensure_teams_and_members works as expected when all of
        the teams already exist, but have no members in them.
        """
        for team in teams_and_members.keys():
            existing_teams[team] = []

        api.ensure_teams_and_members(teams_and_members)

        assert existing_teams == teams_and_members

    @pytest.mark.parametrize('unexpected_exc', [
        exception.GitHubError("", 404),
        exception.GitHubError("", 400),
        exception.GitHubError("", 500)
    ])
    def test_raises_on_non_422_exception(self, api_wrapper_mock, api,
                                         teams_and_members, unexpected_exc):
        """Should raise if anything but a 422 http error is raised when
        creating the team.
        """

        def raise_(*args, **kwargs):
            raise unexpected_exc

        api_wrapper_mock.create_team.side_effect = raise_

        with pytest.raises(exception.UnexpectedException) as exc_info:
            api.ensure_teams_and_members(teams_and_members)

        assert str(unexpected_exc.status) in str(exc_info)

    def test_skips_team_on_422_exception(self, api_wrapper_mock, api,
                                         teams_and_members, existing_teams):
        """422 http error means that the team already exists, so it should just
        be skipped. Here, we verify that it is skipped by it _not_ being adde
        to ``existing_teams``.
        """
        raise_team, *_ = teams_and_members.keys()
        create_team = api_wrapper_mock.create_team.side_effect

        def raise_on_specific(team_name, permission):
            if team_name == raise_team:
                raise exception.GitHubError("", 422)
            create_team(team_name, permission)

        api_wrapper_mock.create_team.side_effect = raise_on_specific

        api.ensure_teams_and_members(teams_and_members)

        del teams_and_members[raise_team]
        assert teams_and_members == existing_teams

    def test_skips_members_already_in_teams(self, api_wrapper_mock, api,
                                            teams_and_members,
                                            existing_teams_prefilled):
        """Test that only members that are not already in their teams are
        added.
        """
        new_members_team_one = teams_and_members['team_one'][:1]
        del existing_teams_prefilled['team_one'][0]
        new_members_last_team = teams_and_members['last_team'][:5]
        existing_teams_prefilled['last_team'] = teams_and_members['last_team'][
            5:]

        expected_calls = [
            call('team_one', new_members_team_one),
            call('last_team', new_members_last_team)
        ]

        api.ensure_teams_and_members(teams_and_members)

        api_wrapper_mock.add_to_team.ensure_has_calls(
            expected_calls, any_order=True)

        def test_no_members_are_added_when_all_teams_filled(
                self, api_wrapper_mock, api, teams_and_members,
                existing_teams_prefilled):
            """Tests that add_to_team is not called if all members are already
            in it."""
            api.ensure_teams_and_members(teams_and_members)

            assert not api_wrapper_mock.add_to_team.called


class TestCreateRepos:
    def test_creates_correct_repos(self, repos, api, api_wrapper_mock):
        """Assert that create_repo is called with the correct arguments."""
        # expect (self, repo_info) call args
        expected_calls = [call(info) for info in repos]

        api.create_repos(repos)

        assert repos
        assert api_wrapper_mock.create_repo.called
        api_wrapper_mock.create_repo.assert_has_calls(expected_calls)

    def test_skips_existing_repos(self, repos, api, api_wrapper_mock):
        """Assert that create_repo is called with all repos even when there are exceptions."""
        create_repo_mock = api_wrapper_mock.create_repo
        expected_calls = [call(info) for info in repos]

        # cause a validation error for the middle repo
        side_effect = [create_repo_mock] * len(expected_calls)
        side_effect[len(repos) // 2] = VALIDATION_ERROR
        create_repo_mock.side_effect = side_effect

        api.create_repos(repos)

        assert repos
        create_repo_mock.assert_has_calls(expected_calls)

    def test_raises_on_unexpected_error(self, repos, api, api_wrapper_mock):
        # a 500 status code is unexpected
        create_repo_mock = api_wrapper_mock.create_repo
        side_effect = [create_repo_mock] * len(repos)
        side_effect_github_exception = [SERVER_ERROR] + side_effect[1:]
        # a general RuntimeError is also unexpected
        side_effect_runtime_error = [RuntimeError()] + side_effect[1:]

        create_repo_mock.side_effect = side_effect_github_exception
        with pytest.raises(exception.GitHubError):
            api.create_repos(repos)

        create_repo_mock.side_effect = side_effect_runtime_error
        with pytest.raises(exception.GitHubError):
            api.create_repos(repos)

    def test_returns_all_urls(self, mocker, repos, api):
        """Assert that create_repo returns the urls for all repos, even if there
        are validation errors.
        """
        expected_urls = [GENERATE_REPO_URL(info.name) for info in repos]

        def create_repo_side_effect(info):
            if info.name != expected_urls[len(expected_urls) // 2]:
                return info.name
            raise VALIDATION_ERROR

        mocker.patch(
            'repomate.github_api.APIWrapper.create_repo',
            side_effect=create_repo_side_effect)
        mocker.patch(
            'repomate.github_api.APIWrapper.get_repo_url',
            side_effect=lambda repo_name: repo_name)

        actual_urls = api.create_repos(repos)
        assert actual_urls == expected_urls


class TestGetRepoUrls:
    """Tests for get_repo_urls."""

    def test_all_repos_found(self, api_wrapper_mock, repos, api):
        repo_names = [repo.name for repo in repos]
        expected_urls = [repo.url for repo in repos]

        urls = api.get_repo_urls(repo_names)

        assert sorted(urls) == sorted(expected_urls)

    @pytest.mark.skip(
        msg=
        "not currently relevant as repo urls are generated, rather than fetched"
    )
    def test_some_repos_found(self, api_wrapper_mock, repos, api):
        found_repo_names = [repo.name for repo in repos[:2]]
        not_found_repo_names = [repo.name for repo in repos[2:]]
        expected_urls = [GENERATE_REPO_URL(name) for name in found_repo_names]
        api_wrapper_mock.get_repos.side_effect = \
            lambda repo_names: [repo for repo in repos if repo.name in found_repo_names]

        urls, not_found = api.get_repo_urls(found_repo_names +
                                            not_found_repo_names)

        assert urls == expected_urls
        assert sorted(not_found) == sorted(not_found_repo_names)


class TestIssueFunctions:
    """Tests for open_issue and close_issue."""

    def test_open_issue(self, api_wrapper_mock, repos, api):
        repo_names = [repo.name for repo in repos]
        api.open_issue(ISSUE.title, ISSUE.body, repo_names)

        api_wrapper_mock.open_issue_in.assert_called_once_with(
            ISSUE, repo_names)

    def test_close_issue(self, api_wrapper_mock, repos, api):
        repo_names = [repo.name for repo in repos]
        regex = "some-regex"
        api.close_issue(regex, repo_names)

        api_wrapper_mock.close_issue_in.assert_called_once_with(
            regex, repo_names)


