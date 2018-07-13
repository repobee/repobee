import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from collections import namedtuple

import github
from gits_pet import github_api
from gits_pet import api_wrapper
from gits_pet import exception
from gits_pet.api_wrapper import RepoInfo

ORG_NAME = "this-is-a-test-org"

NOT_FOUND_EXCEPTION = exception.NotFoundError(msg=None, status=404)
VALIDATION_ERROR = exception.GitHubError(msg=None, status=422)
SERVER_ERROR = exception.GitHubError(msg=None, status=500)


@pytest.fixture(scope='function')
def repo_infos():
    team_names = ('team-one', 'team-two', 'team-three', 'team-four')
    descriptions = ["A nice repo for {}".format(tn) for tn in team_names]
    repo_names = ["{}-week-2".format(tn) for tn in team_names]
    privacy = (True, True, False, True)
    team_id = (1, 2, 3, 55)
    repo_infos = [
        RepoInfo(name, description, private,
                 team_id) for name, description, private, team_id in zip(
                     repo_names, descriptions, privacy, team_id)
    ]
    return repo_infos


@pytest.fixture(scope='function')
def api(mocker):
    # mock out the PyGithub API
    mocker.patch('github.Github', autospec=True)
    return github_api.GitHubAPI('bla', 'blue', 'bli')


@pytest.fixture(scope='function')
def create_repo_mock(mocker):
    create_repo_mock = mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.create_repo',
        autospec=True,
        side_effect=lambda _, info: info.name)
    return create_repo_mock


def test_create_repos_creates_correct_repos(repo_infos, api, create_repo_mock):
    """Assert that create_repo is called with the correct arguments."""
    # expect (self, repo_info) call args
    expected_calls = [call(api._api, info) for info in repo_infos]

    api.create_repos(repo_infos)

    assert repo_infos
    create_repo_mock.assert_has_calls(expected_calls)


def test_create_repos_skips_existing_repos(repo_infos, api, create_repo_mock):
    """Assert that create_repo is called with all repo_infos even when there are exceptions."""
    expected_calls = [call(api._api, info) for info in repo_infos]

    # cause a validation error for the middle repo
    side_effect = [create_repo_mock] * len(expected_calls)
    side_effect[len(repo_infos) // 2] = VALIDATION_ERROR
    create_repo_mock.side_effect = side_effect

    api.create_repos(repo_infos)

    assert repo_infos
    create_repo_mock.assert_has_calls(expected_calls)


def test_create_repos_raises_on_unexpected_error(repo_infos, api,
                                                 create_repo_mock):
    # a 500 status code is unexpected
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


def test_create_repos_returns_all_urls(mocker, repo_infos, api):
    """Assert that create_repo returns the urls for all repos, even if there
    are validation errors.
    """
    # simplify urls to repo names
    expected_urls = [info.name for info in repo_infos]

    def create_repo_side_effect(info):
        if info.name != expected_urls[len(expected_urls) // 2]:
            return info.name
        raise VALIDATION_ERROR

    mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.create_repo',
        side_effect=create_repo_side_effect)
    mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.get_repo_url',
        side_effect=lambda repo_name: repo_name)

    actual_urls = api.create_repos(repo_infos)
    assert actual_urls == expected_urls


def test_ensure_teams_and_members_no_previous_teams(mocker, api):
    """Test that ensure_teams_and_members works as expected with there are no
    previous teams, and all users exist. This is a massive end-to-end test of
    the function with only the lower level API's mocked out.
    """
    # have create_team and get_teams work on a mocked dictionary
    existing_teams = {}
    Team = namedtuple('Team', ['name', 'get_members'])

    def get_teams(self):
        return [Team(tn, MagicMock()) for tn in existing_teams.keys()]

    mock_create_team = mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.create_team',
        autospec=True,
        side_effect=lambda self, team_name, permission: existing_teams.update({team_name: set()})
    )
    mock_get_teams = mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.get_teams',
        autospec=True,
        side_effect=get_teams)
    mock_get_teams_in = mocker.patch('gits_pet.api_wrapper.ApiWrapper.get_teams_in',
            autospec=True,
            side_effect=lambda self, team_names: list(set(team_names).intersection(existing_teams.keys())))
    mock_add_to_team = mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.add_to_team',
        autospec=True,
        side_effect=
        lambda self, username, team: existing_teams[team.name].add(username))

    # get_user just returns the username
    mock_get_user = mocker.patch(
        'gits_pet.api_wrapper.ApiWrapper.get_user',
        autospec=True,
        side_effect=lambda self, username: username)

    teams_and_members = {
        'team_one': set(['first', 'second']),
        'two': set(['two']),
        'last_team': set([str(i) for i in range(10)])
    }

    api.ensure_teams_and_members(teams_and_members)

    assert existing_teams == teams_and_members
