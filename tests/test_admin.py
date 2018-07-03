import sys
import os
import pytest
import subprocess
import string
from asyncio import coroutine
from unittest.mock import patch, PropertyMock, MagicMock
from collections import namedtuple

import gits_pet
from gits_pet import admin
from gits_pet import github_api
from gits_pet import git
from gits_pet import api_wrapper

USER = 'slarse'
ORG_NAME = 'test-org'
GITHUB_BASE_API = 'https://some_enterprise_host/api/v3'

GENERATE_REPO_URL = lambda base_name, student: "https://slarse.se/repos/{}".format(admin.generate_repo_name(base_name, student))


@pytest.fixture(autouse=True)
def git_mock(mocker):
    """Mocks the whole git module so that there are no accidental
    pushes/clones.
    """
    return mocker.patch('gits_pet.admin.git', autospec=True)


@pytest.fixture(autouse=True)
def api_mock(mocker):
    return mocker.patch(
        'gits_pet.admin.GitHubAPI', autospec=True)(GITHUB_BASE_API,
                                                   git.OAUTH_TOKEN, ORG_NAME)


@pytest.fixture(scope='function', autouse=True)
def ensure_teams_and_members_mock(api_mock, students):
    api_mock.ensure_teams_and_members.side_effect = lambda member_lists: [api_wrapper.Team(student, [student], id)
                    for id, student
                    in enumerate(students)]


@pytest.fixture(scope='function')
def master_urls():
    master_urls = [
        'https://someurl.git', 'https://better_url.git',
        'https://another-url.git'
    ]
    return master_urls


@pytest.fixture(scope='function')
def repo_infos(master_urls, students):
    """Students are here used as teams, remember that they have same names as
    students.
    """
    repo_infos = []
    for url in master_urls:
        repo_base_name = admin._repo_name(url)
        repo_infos += [
            github_api.RepoInfo(
                name=admin.generate_repo_name(student, repo_base_name),
                description="{} created for {}".format(repo_base_name,
                                                       student),
                private=True,
                team_id=cur_id) for cur_id, student in enumerate(students)
        ]
    return repo_infos


@pytest.fixture(scope='function')
def push_tuples(master_urls, students):
    push_tuples = []
    base_names = list(map(admin._repo_name, master_urls))
    repo_urls = [
        GENERATE_REPO_URL(base_name, student) for student in students
        for base_name in base_names
    ]
    for url in master_urls:
        repo_base_name = admin._repo_name(url)
        push_tuples += [
            git.Push(
                local_path=repo_base_name,
                remote_url=repo_url,
                branch='master') for repo_url in repo_urls
            if repo_url.endswith(repo_base_name)
        ]
    return push_tuples


@pytest.fixture(scope='function')
def push_tuple_lists(master_urls, students):
    """Create an expected push tuple list for each master url."""
    pts = []
    for url in master_urls:
        repo_base_name = admin._repo_name(url)


@pytest.fixture(scope='function', autouse=True)
def rmtree_mock(mocker):
    return mocker.patch('shutil.rmtree', autospec=True)


@pytest.fixture(scope='function')
def students():
    return list(string.ascii_lowercase)


class TestCreateMultipleStudentRepos:
    """Tests for create_multiple_student_repos."""

    def test_raises_on_duplicate_master_urls(
            self, master_urls, students):
        master_urls.append(master_urls[0])

        with pytest.raises(ValueError) as exc_info:
            admin.create_multiple_student_repos(master_urls, USER, students,
                                                ORG_NAME, GITHUB_BASE_API)
        assert str(exc_info.value) == "master_repo_urls contains duplicates"

    @pytest.mark.parametrize(
        'master_urls, user, students, org_name, github_api_base_url, empty_arg',
        [([], USER, students(), ORG_NAME, GITHUB_BASE_API, 'master_repo_urls'),
         (master_urls(), '', students(), ORG_NAME, GITHUB_BASE_API, 'user'),
         (master_urls(), USER, [], ORG_NAME, GITHUB_BASE_API, 'students'),
         (master_urls(), USER, students(), '', GITHUB_BASE_API, 'org_name'),
         (master_urls(), USER, students(), ORG_NAME, '',
          'github_api_base_url')])
    def test_raises_empty_args(
            self, master_urls, user, students, org_name, github_api_base_url,
            empty_arg):
        """None of the arguments are allowed to be empty."""
        with pytest.raises(ValueError) as exc_info:
            admin.create_multiple_student_repos(master_urls, user, students,
                                                org_name, github_api_base_url)

        assert empty_arg in str(exc_info.value)

    @pytest.mark.parametrize(
        'user, org_name, github_api_base_url, type_error_arg',
        [(31, ORG_NAME, GITHUB_BASE_API, 'user'),
         (USER, 31, GITHUB_BASE_API, 'org_name'),
         (USER, ORG_NAME, 31, 'github_api_base_url')])
    def test_raises_on_invalid_type(
            self, master_urls, user, students, org_name, github_api_base_url,
            type_error_arg):
        """Test that the non-itrable arguments are type checked."""
        with pytest.raises(TypeError) as exc_info:
            admin.create_multiple_student_repos(master_urls, user, students,
                                                org_name, github_api_base_url)
        assert type_error_arg in str(exc_info.value)

    def test(self, master_urls, students,
                                           api_mock, git_mock, repo_infos,
                                           push_tuples, rmtree_mock):
        """Test that create_multiple_student_repos makes the correct function calls."""
        admin.create_multiple_student_repos(master_urls, USER, students,
                                            ORG_NAME, GITHUB_BASE_API)

        for url in master_urls:
            git_mock.clone.assert_any_call(url)
            api_mock.ensure_teams_and_members.assert_called_once_with(
                {student: [student]
                 for student in students})
            rmtree_mock.assert_any_call(admin._repo_name(url))

        api_mock.create_repos.assert_called_once_with(repo_infos)
        git_mock.push_many.assert_called_once_with(push_tuples, user=USER)

    @pytest.mark.skip(msg="Check iterable contents is not yet implemented")
    def test_raises_on_invalid_iterable_contents(
            self):
        pass
