import sys
import os
import pytest
from unittest.mock import patch
from collections import namedtuple

URL_TEMPLATE = 'https://{}github.com/slarse/clanim'
TOKEN = 'besttoken1337'

Env = namedtuple('Env', ['expected_url'])

# import with mocked oauth
with patch('os.getenv', autospec=True, return_value=TOKEN):
    from gits_pet import git


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
    stderr = 'This is pretty bad!'
    # already patched in env_setup fixture
    git.captured_run.return_value = (1, '', stderr)

    with pytest.raises(git.CloneFailedError) as exc:
        git.clone("{}".format(URL_TEMPLATE.format('')))
    assert stderr in str(exc.value)


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
    return Env(expected_url=expected_url)


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
        git.push(1)
    assert 'repo_path' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.push('something', remote=452)
    assert 'remote' in str(exc)
    assert 'expected str' in str(exc)

    with pytest.raises(TypeError) as exc:
        git.push('something', remote='origin', branch=123)
    assert 'branch' in str(exc)
    assert 'expected str' in str(exc)


def test_push_raises_on_empty_repo_path(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('')
    assert 'repo_path must not be empty' in str(exc)


def test_push_raises_on_empty_remote(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('something', remote='')
    assert 'remote must not be empty' in str(exc)


def test_push_raises_on_empty_branch(env_setup):
    with pytest.raises(ValueError) as exc:
        git.push('something', remote='origin', branch='')
    assert 'branch must not be empty' in str(exc)


def test_push_issues_correct_command_with_defaults(env_setup):
    expected_command = "git push origin master".split()
    repo_path = os.sep.join(['path', 'to', 'repo'])

    git.push(repo_path)

    git.run_and_log_stderr_realtime.assert_called_once_with(
        expected_command, cwd=os.path.abspath(repo_path))


def test_push_issues_correct_command(env_setup):
    remote = 'other'
    branch = 'development-branch'
    expected_command = "git push {} {}".format(remote, branch).split()
    repo_path = os.sep.join(['path', 'to', 'repo'])

    git.push(repo_path, remote=remote, branch=branch)

    git.run_and_log_stderr_realtime.assert_called_once_with(
        expected_command, cwd=os.path.abspath(repo_path))


def test_push_raises_on_non_zero_exit_from_git_clone(env_setup, mocker):
    stderr = 'This is pretty bad indeed!'
    # already patched in env_setup fixture
    git.run_and_log_stderr_realtime.return_value = (1, stderr)

    with pytest.raises(git.PushFailedError) as exc:
        git.push('some_repo')
    assert stderr in str(exc.value)


def test_add_push_remotes_raises_on_non_str_repo_path(env_setup):
    with pytest.raises(TypeError) as exc:
        git.add_push_remotes(2, 'slarse', tuple())
    assert 'repo_path' in str(exc)
    assert 'expected str' in str(exc)


def test_add_push_remotes_raises_on_empty_repo_path(env_setup):
    with pytest.raises(ValueError) as exc:
        git.add_push_remotes('', 'slarse',
                             [('origin', 'https://github.com/slarse/clanim')])
    assert 'repo_path must not be empty' in str(exc)


def test_add_push_remotes_raises_on_non_str_user(env_setup):
    with pytest.raises(TypeError) as exc:
        git.add_push_remotes('some_repo', 32, tuple())
    assert 'user' in str(exc)
    assert 'expected str' in str(exc)


def test_add_push_remotes_raises_on_empty_user(env_setup):
    with pytest.raises(ValueError) as exc:
        git.add_push_remotes('some_repo', '',
                             [('origin', 'https://github.com/slarse/clanim')])
    assert 'user must not be empty' in str(exc)


def test_add_push_remotes_raises_on_empty_remotes(env_setup):
    with pytest.raises(ValueError) as exc:
        git.add_push_remotes('something', 'slarse', [])
    assert 'remotes' in str(exc)


def test_add_push_remotes_raises_on_bad_remotes_formatting(env_setup):
    repo = 'something'
    # second tuple has too many values
    remotes_bad_length = (('origin', 'https://byebye.com'),
                          ('origin', 'https://hello.com', 'byeby'))

    # third tuple has an int as remote
    remotes_bad_type = (('origin', 'https://byebye.com'),
                        ('origin', 'https://hello.com'), (2,
                                                          'https://slarse.se'))
    with pytest.raises(ValueError) as exc_bad_length:
        git.add_push_remotes(repo, 'slarse', remotes_bad_length)

    with pytest.raises(ValueError) as exc_bad_type:
        git.add_push_remotes(repo, 'slarse', remotes_bad_type)

    assert str(remotes_bad_length[1]) in str(exc_bad_length)
    assert str(remotes_bad_type[2]) in str(exc_bad_type)


def test_add_push_remotes(env_setup):
    repo = os.sep.join(['some', 'repo', 'path'])
    user = 'slarse'
    remotes = (('origin', 'https://slarse.se/repo'),
               ('origin', 'https://github.com/slarse/repo'),
               ('other', 'https://github.com/slarse/repo'))

    expected_commands = [
        "git remote set-url --add --push {} {}".format(
            remote, git._insert_user_and_token(url, user, TOKEN)).split()
        for remote, url in remotes
    ]
    git.add_push_remotes(repo, user, remotes)

    for command in expected_commands:
        git.captured_run.assert_any_call(command, cwd=os.path.abspath(repo))


def test_add_push_remotes_raises_on_non_zero_exit_from_git(env_setup):
    stderr = 'bad for push remotes'
    git.captured_run.return_value = (23, '', stderr)
    repo = os.sep.join(['some', 'repo', 'path'])
    remotes = (('origin', 'https://slarse.se/repo'),
               ('origin', 'https://github.com/slarse/repo'),
               ('other', 'https://github.com/slarse/repo'))

    with pytest.raises(git.GitError) as exc:
        git.add_push_remotes(repo, 'slarse', remotes)
    assert stderr in str(exc.value)
