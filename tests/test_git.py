import sys
import os
import pytest
import subprocess
from asyncio import coroutine
from unittest.mock import patch, PropertyMock, MagicMock
from collections import namedtuple

URL_TEMPLATE = 'https://{}github.com/slarse/clanim'
TOKEN = 'besttoken1337'
USER = 'slarse'

Env = namedtuple('Env', ('expected_url', 'expected_url_with_username'))

AioSubproc = namedtuple('AioSubproc', ('create_subprocess', 'process'))

# import with mocked oauth
with patch('os.getenv', autospec=True, return_value=TOKEN):
    from gits_pet import git


@pytest.fixture(scope='function')
def env_setup(mocker):
    mocker.patch(
        'gits_pet.git.captured_run', autospec=True, return_value=(0, '', ''))
    mocker.patch(
        'gits_pet.git.run_and_log_stderr_realtime',
        autospec=True,
        return_value=(0, ''))
    # TOKEN was mocked as the environment token when gits_pet.git was imported
    expected_url = URL_TEMPLATE.format(TOKEN + '@')
    expected_url_with_username = URL_TEMPLATE.format("{}:{}@".format(
        USER, TOKEN))
    return Env(
        expected_url=expected_url,
        expected_url_with_username=expected_url_with_username)


@pytest.fixture(scope='function')
def aio_subproc(mocker):
    class Process:
        async def communicate(self):
            return b"this is stdout", b"this is stderr"

        returncode = 0

    async def mock_gen():
        return Process()

    create_subprocess = mocker.patch(
        'asyncio.create_subprocess_exec', return_value=mock_gen())
    return AioSubproc(create_subprocess, Process)


@pytest.fixture(scope='function')
def push_tuples():
    paths = (os.path.join(*dirs)
             for dirs in [('some', 'awesome', 'path'), ('other',
                                                        'path'), ('final', )])
    urls = ('https://slarse.se/best-repo.git',
            'https://completely-imaginary-repo-url.com/repo.git',
            'https://somerepourl.git')
    branches = ('master', 'other', 'development-branch')
    tups = [
        git.Push(local_path=path, remote_url=url, branch=branch)
        for path, url, branch in zip(paths, urls, branches)
    ]
    return tups


def test_insert_token():
    token = '1209487fbfuq324yfqf78b6'
    assert git._insert_token(URL_TEMPLATE.format(''),
                             token) == URL_TEMPLATE.format(token + '@')


def test_insert_empty_token_raises():
    with pytest.raises(ValueError) as exc:
        git._insert_token(URL_TEMPLATE.format(''), '')
    assert 'empty token' in str(exc)


def test_insert_token_raises_for_non_https():
    with pytest.raises(ValueError) as exc:
        git._insert_token('www.google.com', '124124vfgh23')
    assert 'https://' in str(exc)


def test_clone_raises_on_type_errors(env_setup):
    with pytest.raises(TypeError) as exc:
        git.clone(32)
    assert 'repo_url is of type' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.clone('blabla', 8)
    assert 'single_branch is of type' in str(exc)
    assert 'expected bool'

    with pytest.raises(TypeError) as exc:
        git.clone('blabla', True, 32)
    assert 'branch is of type' in str(exc)
    assert 'expected NoneType or str'


def test_clone_raises_on_empty_branch(env_setup):
    with pytest.raises(ValueError) as exc:
        git.clone(URL_TEMPLATE.format(''), branch='')
    assert 'branch must not be empty' in str(exc)


def test_clone_raises_on_non_zero_exit_from_git_clone(env_setup, mocker):
    stderr = b'This is pretty bad!'
    # already patched in env_setup fixture
    git.captured_run.return_value = (1, '', stderr)

    with pytest.raises(git.CloneFailedError) as exc:
        git.clone("{}".format(URL_TEMPLATE.format('')))
    assert "Failed to clone" in str(exc.value)


def test_clone_issues_correct_command_with_defaults(env_setup):
    expected_command = "git clone {} --single-branch".format(
        env_setup.expected_url).split()

    git.clone(URL_TEMPLATE.format(''))
    git.captured_run.assert_called_once_with(expected_command)


def test_clone_issues_correct_command_without_single_branch(env_setup):
    expected_command = "git clone {}".format(env_setup.expected_url).split()

    git.clone(URL_TEMPLATE.format(''), single_branch=False)
    git.captured_run.assert_called_once_with(expected_command)


def test_clone_issues_correct_command_with_single_other_branch(env_setup):
    branch = 'other-branch'
    expected_command = "git clone {} --single-branch -b {}".format(
        env_setup.expected_url, branch).split()

    git.clone(URL_TEMPLATE.format(''), single_branch=True, branch=branch)
    git.captured_run.assert_called_once_with(expected_command)


def test_push_raises_on_non_string_args(env_setup):
    with pytest.raises(TypeError) as exc:
        git.push(1, user=USER, repo_url='some_url')
    assert 'local_repo' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.push('something', user=2, repo_url='some_url')
    assert 'user' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.push('something', user=USER, repo_url=1)
    assert 'repo_url' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.push('something', user=USER, repo_url='some_url', branch=3)
    assert 'branch' in str(exc)
    assert 'expected str' in str(exc)


def test_push_raises_on_empty_local_repo(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('', user=USER, repo_url='some_url')
    assert 'local_repo must not be empty' in str(exc)


def test_push_raises_on_empty_user(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('something', user='', repo_url='some_url')
    assert 'user must not be empty' in str(exc)


def test_push_raises_on_empty_repo_url(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('something', user=USER, repo_url='')
    assert 'repo_url must not be empty' in str(exc)


def test_push_raises_on_empty_branch(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('something', user=USER, repo_url='some_url', branch='')
    assert 'branch must not be empty' in str(exc)


def test_push_raises_on_async_push_exception(env_setup, mocker):
    async def raise_(*args, **kwargs):
        raise git.PushFailedError("Push failed", 128, b"some error")

    mocker.patch('gits_pet.git._push_async', side_effect=raise_)

    with pytest.raises(git.PushFailedError) as exc_info:
        git.push('some_repo', USER, 'some_url')


def test_push_issues_correct_command_with_defaults(env_setup, aio_subproc):
    branch = 'master'
    user = USER
    local_repo = os.sep.join(['path', 'to', 'repo'])
    expected_command = "git push {} {}".format(
        env_setup.expected_url_with_username, branch).split()

    git.push(
        local_repo, user=user, repo_url=URL_TEMPLATE.format(''), branch=branch)

    aio_subproc.create_subprocess.assert_called_once_with(
        *expected_command,
        cwd=os.path.abspath(local_repo),
        # TODO the piping is not obvious from the test, refactor
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)


def test_push_issues_correct_command(env_setup, aio_subproc):
    branch = 'development-branch'
    user = USER
    expected_command = "git push {} {}".format(
        env_setup.expected_url_with_username, branch).split()
    local_repo = os.sep.join(['path', 'to', 'repo'])

    git.push(
        local_repo, user=user, repo_url=URL_TEMPLATE.format(''), branch=branch)

    aio_subproc.create_subprocess.assert_called_once_with(
        *expected_command,
        cwd=os.path.abspath(local_repo),
        # TODO the piping is not obvious from the test, refactor
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)


def test_push_raises_on_non_zero_exit_from_git_push(env_setup, aio_subproc):
    aio_subproc.process.returncode = 128

    with pytest.raises(git.PushFailedError) as exc:
        git.push(
            'some_repo', user='some_user', repo_url='https://some_url.org')


def test_push_many_raises_on_non_str_user(env_setup, push_tuples):
    with pytest.raises(TypeError) as exc_info:
        git.push_many(push_tuples, 32)
    assert 'user' in str(exc_info)


def test_push_many_raises_on_empty_push_tuples(env_setup):
    with pytest.raises(ValueError) as exc_info:
        git.push_many([], USER)
    assert 'push_tuples' in str(exc_info)


def test_push_many_raises_on_empty_user(env_setup, push_tuples):
    with pytest.raises(ValueError) as exc_info:
        git.push_many(push_tuples, '')
    assert 'user' in str(exc_info)


def test_push_many(env_setup, push_tuples, aio_subproc):
    """Test that push many works as expected when no exceptions are thrown by
    tasks.
    """
    expected_subproc_commands = [(local_repo, "git push {} {}".format(
        git._insert_user_and_token(url, USER), branch).split())
                                 for local_repo, url, branch in push_tuples]

    git.push_many(push_tuples, USER)

    for local_repo, command in expected_subproc_commands:
        aio_subproc.create_subprocess.assert_any_call(
            *command,
            cwd=os.path.abspath(local_repo),
            # TODO again, the piping here is not obvious
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)


def test_push_many_tries_all_calls_despite_exceptions(env_setup, push_tuples,
                                                      mocker):
    """Test that push_many tries to push all push tuple values even if there
    are exceptions.
    """

    async def raise_(*args, **kwargs):
        raise git.PushFailedError("Push failed", 128, b"some error")

    mocker.patch('gits_pet.git._push_async', side_effect=raise_)

    git.push_many(push_tuples, USER)

    for pt in push_tuples:
        git._push_async.assert_any_call(pt.local_path, USER, pt.remote_url,
                                        pt.branch)
