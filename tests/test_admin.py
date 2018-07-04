import sys
import os
import pytest
import tempfile
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

GENERATE_REPO_URL = lambda base_name, student:\
        "https://slarse.se/repos/{}".format(
            admin.generate_repo_name(base_name, student))


@pytest.fixture()
def git_mock(request, mocker):
    """Mocks the whole git module so that there are no accidental
    pushes/clones.
    """
    if 'nogitmock' in request.keywords:
        return
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
def master_names(master_urls):
    return [admin._repo_name(url) for url in master_urls]


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
    return list(string.ascii_lowercase)[:10]


def assert_raises_on_duplicate_master_urls(function, master_urls, students):
    """Test for functions that take master_urls and students args."""

    master_urls.append(master_urls[0])

    with pytest.raises(ValueError) as exc_info:
        function(master_urls, USER, students, ORG_NAME, GITHUB_BASE_API)
    assert str(exc_info.value) == "master_repo_urls contains duplicates"


RAISES_ON_EMPTY_ARGS_PARAMETRIZATION = (
    'master_urls, user, students, org_name, github_api_base_url, empty_arg',
    [([], USER, students(), ORG_NAME, GITHUB_BASE_API, 'master_repo_urls'),
     (master_urls(), '', students(), ORG_NAME, GITHUB_BASE_API, 'user'),
     (master_urls(), USER, [], ORG_NAME, GITHUB_BASE_API,
      'students'), (master_urls(), USER, students(), '',
                    GITHUB_BASE_API, 'org_name'), (master_urls(), USER,
                                                   students(), ORG_NAME, '',
                                                   'github_api_base_url')])
RAISES_ON_EMPTY_ARGS_IDS = [
    "|".join([str(val) for val in line])
    for line in RAISES_ON_EMPTY_ARGS_PARAMETRIZATION[1]
]

RAISES_ON_INVALID_TYPE_PARAMETRIZATION = (
    'user, org_name, github_api_base_url, type_error_arg',
    [(31, ORG_NAME, GITHUB_BASE_API, 'user'),
     (USER, 31, GITHUB_BASE_API, 'org_name'), (USER, ORG_NAME, 31,
                                               'github_api_base_url')])

RAISES_ON_EMPTY_INVALID_TYPE_IDS = [
    "|".join([str(val) for val in line])
    for line in RAISES_ON_INVALID_TYPE_PARAMETRIZATION[1]
]


class TestCreateMultipleStudentRepos:
    """Tests for create_multiple_student_repos."""

    def test_raises_on_duplicate_master_urls(self, master_urls, students):
        assert_raises_on_duplicate_master_urls(
            admin.create_multiple_student_repos, master_urls, students)

    @pytest.mark.parametrize(
        *RAISES_ON_EMPTY_ARGS_PARAMETRIZATION, ids=RAISES_ON_EMPTY_ARGS_IDS)
    def test_raises_empty_args(self, master_urls, user, students, org_name,
                               github_api_base_url, empty_arg):
        """None of the arguments are allowed to be empty."""
        with pytest.raises(ValueError) as exc_info:
            admin.create_multiple_student_repos(master_urls, user, students,
                                                org_name, github_api_base_url)

    @pytest.mark.parametrize(
        *RAISES_ON_INVALID_TYPE_PARAMETRIZATION,
        ids=RAISES_ON_EMPTY_INVALID_TYPE_IDS)
    def test_raises_on_invalid_type(self, master_urls, user, students,
                                    org_name, github_api_base_url,
                                    type_error_arg):
        """Test that the non-itrable arguments are type checked."""
        with pytest.raises(TypeError) as exc_info:
            admin.create_multiple_student_repos(master_urls, user, students,
                                                org_name, github_api_base_url)
        assert type_error_arg in str(exc_info.value)

    def test_happy_path(self, master_urls, students, api_mock, git_mock,
                        repo_infos, push_tuples, rmtree_mock):
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
        git_mock.push.assert_called_once_with(push_tuples, user=USER)

    @pytest.mark.skip(msg="Check iterable contents is not yet implemented")
    def test_raises_on_invalid_iterable_contents(self):
        pass


class TestUpdateStudentRepos:
    """Tests for update_student_repos."""

    def test_raises_on_duplicate_master_urls(self, master_urls, students):
        assert_raises_on_duplicate_master_urls(admin.update_student_repos,
                                               master_urls, students)

    @pytest.mark.parametrize(
        *RAISES_ON_EMPTY_ARGS_PARAMETRIZATION, ids=RAISES_ON_EMPTY_ARGS_IDS)
    def test_raises_empty_args(self, master_urls, user, students, org_name,
                               github_api_base_url, empty_arg):
        """None of the arguments are allowed to be empty."""
        with pytest.raises(ValueError) as exc_info:
            admin.update_student_repos(master_urls, user, students, org_name,
                                       github_api_base_url)
        assert empty_arg in str(exc_info)

    @pytest.mark.parametrize(
        *RAISES_ON_INVALID_TYPE_PARAMETRIZATION,
        ids=RAISES_ON_EMPTY_INVALID_TYPE_IDS)
    def test_raises_on_invalid_type(self, master_urls, user, students,
                                    org_name, github_api_base_url,
                                    type_error_arg):
        """Test that the non-iterable arguments are type checked."""
        with pytest.raises(TypeError) as exc_info:
            admin.update_student_repos(master_urls, user, students, org_name,
                                       github_api_base_url)
        assert type_error_arg in str(exc_info.value)

    def test_happy_path(self, master_urls, students, api_mock, git_mock,
                        repo_infos, push_tuples, rmtree_mock):
        """Test that update_student_repos makes the correct function calls."""
        admin.update_student_repos(master_urls, USER, students, ORG_NAME,
                                   GITHUB_BASE_API)

        for url in master_urls:
            git_mock.clone.assert_any_call(url)
            rmtree_mock.assert_any_call(admin._repo_name(url))

        git_mock.push.assert_called_once_with(push_tuples, user=USER)

    @pytest.mark.nogitmock
    @pytest.mark.parametrize(
        'issue',
        [admin.Issue("Oops", "Sorry, we failed to push to your repo!"), None])
    def test_issues_on_exceptions(self, issue, mocker, api_mock, repo_infos,
                                  push_tuples, rmtree_mock):
        """Test that issues are opened in repos where pushing fails, if and only if
        the issue is not None.
        
        IMPORTANT NOTE: the git_mock fixture is ignored in this test. Be careful.
        """
        students = list('abc')
        master_name = 'week-1'
        master_urls = [
            'https://some-host/repos/{}'.format(name)
            for name in [master_name, 'week-3']
        ]

        generate_url = lambda repo_name: "{}/{}/{}".format(GITHUB_BASE_API, ORG_NAME, repo_name)
        fail_repo_names = [
            admin.generate_repo_name(stud, master_name) for stud in ['a', 'c']
        ]
        fail_repo_urls = [generate_url(name) for name in fail_repo_names]

        api_mock.get_repo_urls.side_effect = lambda repo_names: [generate_url(name) for name in repo_names]

        async def raise_specific(local_repo, user, repo_url, branch):
            if repo_url in fail_repo_urls:
                raise git.PushFailedError("Push failed", 128, b"some error",
                                          repo_url)

        git_push_async_mock = mocker.patch(
            'gits_pet.git._push_async', side_effect=raise_specific)
        git_clone_mock = mocker.patch('gits_pet.git.clone')

        admin.update_student_repos(master_urls, USER, students, ORG_NAME,
                                   GITHUB_BASE_API, issue)

        if issue:  # expect issue to be opened
            api_mock.open_issue.assert_called_once_with(
                issue.title, issue.body, fail_repo_names)
        else:  # expect issue not to be opened
            assert not api_mock.open_issue.called

    @pytest.mark.nogitmock
    def test_issues_arent_opened_on_exceptions_if_unspeficied(
            self, mocker, api_mock, repo_infos, push_tuples, rmtree_mock):
        """Test that issues are not opened in repos where pushing fails, no
        issue has been given.
        
        IMPORTANT NOTE: the git_mock fixture is ignored in this test. Be careful.
        """
        students = list('abc')
        master_name = 'week-1'
        master_urls = [
            'https://some-host/repos/{}'.format(name)
            for name in [master_name, 'week-3']
        ]

        generate_url = lambda repo_name: "{}/{}/{}".format(GITHUB_BASE_API, ORG_NAME, repo_name)
        fail_repo_names = [
            admin.generate_repo_name(stud, master_name) for stud in ['a', 'c']
        ]
        fail_repo_urls = [generate_url(name) for name in fail_repo_names]

        api_mock.get_repo_urls.side_effect = lambda repo_names: [generate_url(name) for name in repo_names]
        issue = admin.Issue("Oops", "Sorry, we failed to push to your repo!")

        async def raise_specific(local_repo, user, repo_url, branch):
            if repo_url in fail_repo_urls:
                raise git.PushFailedError("Push failed", 128, b"some error",
                                          repo_url)

        git_push_async_mock = mocker.patch(
            'gits_pet.git._push_async', side_effect=raise_specific)
        git_clone_mock = mocker.patch('gits_pet.git.clone')

        admin.update_student_repos(master_urls, USER, students, ORG_NAME,
                                   GITHUB_BASE_API, issue)

        api_mock.open_issue.assert_called_once_with(issue.title, issue.body,
                                                    fail_repo_names)


class TestOpenIssue:
    """Tests for open_issue."""

    # TODO expand to also test org_name and github_api_base_url
    # can probably use the RAISES_ON_EMPTY_ARGS_PARAMETRIZATION for that,
    # somehow
    @pytest.mark.parametrize(
        'master_repo_names, students, issue, org_name, github_api_base_url, empty_arg',
        [
            ([], students(), admin.Issue('', ''), ORG_NAME, GITHUB_BASE_API,
             'master_repo_names'),
            (master_names(master_urls()), [], admin.Issue('', ''), ORG_NAME,
             GITHUB_BASE_API, 'students'),
            (master_names(master_urls()), students(), None, ORG_NAME,
             GITHUB_BASE_API, 'issue'),
        ])
    def test_raises_on_empty_args(self, master_repo_names, students, issue,
                                  org_name, github_api_base_url, empty_arg):
        with pytest.raises(ValueError) as exc_info:
            admin.open_issue(master_repo_names, students, issue, org_name,
                             github_api_base_url)
        assert empty_arg in str(exc_info)

    def test_happy_path(self, api_mock):
        title = "Best title"
        body = "This is some **cool** markdown\n\n### Heading!"
        master_names = ['week-1', 'week-2']
        students = list('abc')
        expected_repo_names = [
            'a-week-1', 'b-week-1', 'c-week-1', 'a-week-2', 'b-week-2',
            'c-week-2'
        ]

        issue = admin.Issue(
            "A title", "And a nice **formatted** body\n### With headings!")
        admin.open_issue(master_names, students, issue, ORG_NAME,
                         GITHUB_BASE_API)

        api_mock.open_issue.assert_called_once_with(issue.title, issue.body,
                                                    expected_repo_names)


class TestCloseIssue:
    """Tests for close_issue."""

    @pytest.mark.parametrize(
        'master_repo_names, students, org_name, github_api_base_url, empty_arg',
        [
            ([], students(), ORG_NAME, GITHUB_BASE_API, 'master_repo_names'),
            (master_names(master_urls()), [], ORG_NAME, GITHUB_BASE_API,
             'students'),
            (master_names(master_urls()), students(), '', GITHUB_BASE_API,
             'org_name'),
            (master_names(master_urls()), students(), ORG_NAME, '',
             'github_api_base_url'),
        ])
    def test_raises_on_empty_args(self, master_repo_names, students, org_name,
                                  github_api_base_url, empty_arg):
        """only the regex is allowed ot be empty."""
        with pytest.raises(ValueError) as exc_info:
            admin.close_issue('someregex', master_repo_names, students,
                              org_name, github_api_base_url)
        assert empty_arg in str(exc_info)

    @pytest.mark.parametrize('org_name, github_api_base_url, type_error_arg', [
        (2, GITHUB_BASE_API, 'org_name'),
        (ORG_NAME, 41, 'github_api_base_url'),
    ])
    def test_raises_on_invalid_type(self, master_names, org_name,
                                    github_api_base_url, type_error_arg):
        """Test that the non-itrable arguments are type checked."""
        with pytest.raises(TypeError) as exc_info:
            admin.close_issue('someregex', master_names, students, org_name,
                              github_api_base_url)
        assert type_error_arg in str(exc_info.value)

    def test_happy_path(self, api_mock):
        title_regex = r"some-regex\d\w"
        master_names = ['week-1', 'week-2']
        students = list('abc')
        expected_repo_names = [
            'a-week-1', 'b-week-1', 'c-week-1', 'a-week-2', 'b-week-2',
            'c-week-2'
        ]

        admin.close_issue(title_regex, master_names, students, ORG_NAME,
                          GITHUB_BASE_API)

        api_mock.close_issue.assert_called_once_with(title_regex,
                                                     expected_repo_names)
