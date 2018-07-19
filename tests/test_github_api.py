import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from collections import namedtuple

import github
from gits_pet import github_api
from gits_pet import exception
from gits_pet import tuples

ORG_NAME = "this-is-a-test-org"

NOT_FOUND_EXCEPTION = exception.NotFoundError(msg=None, status=404)
VALIDATION_ERROR = exception.GitHubError(msg=None, status=422)
SERVER_ERROR = exception.GitHubError(msg=None, status=500)

GENERATE_REPO_URL = pytest.functions.GENERATE_REPO_URL


@pytest.fixture(scope='function')
def repo_infos():
    team_names = ('team-one', 'team-two', 'team-three', 'team-four')
    descriptions = ["A nice repo for {}".format(tn) for tn in team_names]
    repo_names = ["{}-week-2".format(tn) for tn in team_names]
    privacy = (True, True, False, True)
    team_id = (1, 2, 3, 55)
    repo_infos = [
        tuples.Repo(name, description, private,
                 team_id) for name, description, private, team_id in zip(
                     repo_names, descriptions, privacy, team_id)
    ]
    return repo_infos


@pytest.fixture
def existing_teams():
    existing_teams = {}
    yield existing_teams


@pytest.fixture
def api_wrapper_mock(mocker, existing_teams):
    api_wrapper_instance = MagicMock()

    # have create_team and get_teams work on a mocked dictionary
    api_wrapper_instance.create_repo.side_effect = \
        lambda repo_info: GENERATE_REPO_URL(repo_info.name)
    api_wrapper_instance.create_team.side_effect = \
        lambda team_name, permission: existing_teams.update({team_name: set()})

    api_wrapper_instance.get_teams.side_effect = \
        lambda: [tuples.Team(name=name, members=members, id=hash(name)) for name, members in existing_teams.items()]

    api_wrapper_instance.get_teams_in.side_effect = \
        lambda team_names: list(set(team_names).intersection(existing_teams.keys()))

    def add_to_team(members, team):
        for user in members:
            existing_teams[team.name].add(user)

    api_wrapper_instance.add_to_team.side_effect = add_to_team

    api_wrapper_instance.get_user.side_effect = lambda username: username

    api_wrapper_instance.get_repo_url.side_effect = \
        lambda repo_name: GENERATE_REPO_URL(repo_name)

    api_wrapper_mock = mocker.patch(
        'gits_pet.github_api.APIWrapper', return_value=api_wrapper_instance)

    return api_wrapper_instance


@pytest.fixture(scope='function')
def api(api_wrapper_mock, mocker):
    return github_api.GitHubAPI('bla', 'blue', 'bli')


class TestEnsureTeamsAndMembers:
    def test_no_previous_teams(self, api_wrapper_mock, existing_teams, api):
        """Test that ensure_teams_and_members works as expected when there are no
        previous teams, and all users exist. This is a massive end-to-end test of
        the function with only the lower level API's mocked out.
        """
        teams_and_members = {
            'team_one': set(['first', 'second']),
            'two': set(['two']),
            'last_team': set([str(i) for i in range(10)])
        }

        api.ensure_teams_and_members(teams_and_members)

        assert existing_teams == teams_and_members


class TestCreateRepos:
    def test_creates_correct_repos(self, repo_infos, api, api_wrapper_mock):
        """Assert that create_repo is called with the correct arguments."""
        # expect (self, repo_info) call args
        expected_calls = [call(info) for info in repo_infos]

        api.create_repos(repo_infos)

        assert repo_infos
        assert api_wrapper_mock.create_repo.called
        api_wrapper_mock.create_repo.assert_has_calls(expected_calls)

    def test_skips_existing_repos(self, repo_infos, api, api_wrapper_mock):
        """Assert that create_repo is called with all repo_infos even when there are exceptions."""
        create_repo_mock = api_wrapper_mock.create_repo
        expected_calls = [call(info) for info in repo_infos]

        # cause a validation error for the middle repo
        side_effect = [create_repo_mock] * len(expected_calls)
        side_effect[len(repo_infos) // 2] = VALIDATION_ERROR
        create_repo_mock.side_effect = side_effect

        api.create_repos(repo_infos)

        assert repo_infos
        create_repo_mock.assert_has_calls(expected_calls)

    def test_raises_on_unexpected_error(self, repo_infos, api,
                                        api_wrapper_mock):
        # a 500 status code is unexpected
        create_repo_mock = api_wrapper_mock.create_repo
        side_effect = [create_repo_mock] * len(repo_infos)
        side_effect_github_exception = [SERVER_ERROR] + side_effect[1:]
        # a general RuntimeError is also unexpected
        side_effect_runtime_error = [RuntimeError()] + side_effect[1:]

        create_repo_mock.side_effect = side_effect_github_exception
        with pytest.raises(exception.GitHubError):
            api.create_repos(repo_infos)

        create_repo_mock.side_effect = side_effect_runtime_error
        with pytest.raises(exception.GitHubError):
            api.create_repos(repo_infos)

    def test_returns_all_urls(self, mocker, repo_infos, api):
        """Assert that create_repo returns the urls for all repos, even if there
        are validation errors.
        """
        expected_urls = [GENERATE_REPO_URL(info.name) for info in repo_infos]

        def create_repo_side_effect(info):
            if info.name != expected_urls[len(expected_urls) // 2]:
                return info.name
            raise VALIDATION_ERROR

        mocker.patch(
            'gits_pet.github_api.APIWrapper.create_repo',
            side_effect=create_repo_side_effect)
        mocker.patch(
            'gits_pet.github_api.APIWrapper.get_repo_url',
            side_effect=lambda repo_name: repo_name)

        actual_urls = api.create_repos(repo_infos)
        assert actual_urls == expected_urls
