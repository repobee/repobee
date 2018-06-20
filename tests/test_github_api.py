import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from collections import namedtuple

import github
from gits_pet import github_api
from gits_pet.github_api import RepoInfo

ORG_NAME = "this-is-a-test-org"

NOT_FOUND_EXCEPTION = github.GithubException(data=None, status=404)
VALIDATION_ERROR_EXCEPTION = github.GithubException(data=None, status=422)
SERVER_ERROR_EXCEPTION = github.GithubException(data=None, status=500)


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
def api_mock(mocker):
    api_mock = mocker.patch('gits_pet.github_api._API', autospec=True)
    return api_mock


def test_create_repos_creates_correct_repos(repo_infos, api_mock):
    """Assert that create_repos is called with the correct arguments."""
    create_repo_mock = api_mock.get_organization(ORG_NAME).create_repo
    expected_calls = [
        call(
            info.name,
            description=info.description,
            private=info.private,
            team_id=info.team_id) for info in repo_infos
    ]

    github_api.create_repos(repo_infos, ORG_NAME)

    assert repo_infos
    create_repo_mock.assert_has_calls(expected_calls)


def test_create_repos_skips_existing_repos(repo_infos, api_mock):
    """Assert that create_repos is called with all repo_infos even when there are exceptions."""
    create_repo_mock = api_mock.get_organization(ORG_NAME).create_repo
    expected_calls = [
        call(
            info.name,
            description=info.description,
            private=info.private,
            team_id=info.team_id) for info in repo_infos
    ]

    # cause a validation error for the middle repo
    side_effect = [create_repo_mock] * len(expected_calls)
    side_effect[len(repo_infos) // 2] = VALIDATION_ERROR_EXCEPTION
    create_repo_mock.side_effect = side_effect

    github_api.create_repos(repo_infos, ORG_NAME)

    assert repo_infos
    create_repo_mock.assert_has_calls(expected_calls)


def test_create_repos_raises_on_unexpected_error(repo_infos, api_mock):
    create_repo_mock = api_mock.get_organization(ORG_NAME).create_repo

    # a 500 status code is unexpected
    side_effect = [create_repo_mock] * len(repo_infos)
    side_effect_github_exception = [SERVER_ERROR_EXCEPTION] + side_effect[1:]
    side_effect_runtime_error = [RuntimeError()] + side_effect[1:]

    create_repo_mock.side_effect = side_effect_github_exception
    with pytest.raises(github_api.GitHubError):
        github_api.create_repos(repo_infos, ORG_NAME)

    create_repo_mock.side_effect = side_effect_runtime_error
    with pytest.raises(github_api.GitHubError):
        github_api.create_repos(repo_infos, ORG_NAME)


def test_create_repos_raises_githuberror_on_get_org_404(repo_infos, api_mock):
    api_mock.get_organization.side_effect = [NOT_FOUND_EXCEPTION]
    with pytest.raises(github_api.GitHubError) as exc:
        github_api.create_repos(repo_infos, ORG_NAME)
    assert exc.value.status == 404


def test_create_repos_returns_all_urls(mocker, repo_infos, api_mock):
    """Assert that create_repos returns the urls for all repos, even if there
    are validation errors.
    """
    # simplify urls to repo names
    expected_urls = [info.name for info in repo_infos]

    def create_repo_side_effect(info, _):
        if info.name != expected_urls[len(expected_urls) // 2]:
            return info.name
        raise github_api.GitHubError(status=422)

    mocker.patch(
        'gits_pet.github_api._create_repo',
        side_effect=create_repo_side_effect)
    mocker.patch(
        'gits_pet.github_api._get_repo_url',
        side_effect=lambda repo_name, _: repo_name)

    actual_urls = github_api.create_repos(repo_infos, ORG_NAME)
    assert actual_urls == expected_urls
