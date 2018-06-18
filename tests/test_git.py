import sys
import os
import pytest
from collections import namedtuple
from gits_pet import git

URL_TEMPLATE = 'https://{}github.com/slarse/clanim'

Env = namedtuple('Env', ['expected_url'])


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
    git.captured_run.return_value = (1, b'', stderr)

    with pytest.raises(git.CloneFailedError) as exc:
        git.clone("{}".format(URL_TEMPLATE.format('')))
    assert stderr.decode(encoding=sys.getdefaultencoding()) in str(exc.value)


@pytest.fixture(scope='function')
def env_setup(mocker, monkeypatch):
    token = 'besttoken1337'
    monkeypatch.setattr('gits_pet.git.OAUTH_TOKEN', token)
    mocker.patch(
        'gits_pet.git.captured_run', autospec=True, return_value=(0, b'', b''))
    expected_url = URL_TEMPLATE.format(token + '@')
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

    git.captured_run.assert_called_once_with(
        expected_command, cwd=os.path.abspath(repo_path))


def test_push_issues_correct_command(env_setup):
    remote = 'other'
    branch = 'development-branch'
    expected_command = "git push {} {}".format(remote, branch).split()
    repo_path = os.sep.join(['path', 'to', 'repo'])

    git.push(repo_path, remote=remote, branch=branch)

    git.captured_run.assert_called_once_with(
        expected_command, cwd=os.path.abspath(repo_path))


def test_push_raises_on_non_zero_exit_from_git_clone(env_setup, mocker):
    stderr = b'This is pretty bad indeed!'
    # already patched in env_setup fixture
    git.captured_run.return_value = (1, b'', stderr)

    with pytest.raises(git.PushFailedError) as exc:
        git.push('some_repo')
    assert stderr.decode(encoding=sys.getdefaultencoding()) in str(exc.value)
