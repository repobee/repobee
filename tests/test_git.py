import sys
import pytest
from collections import namedtuple
from gits_pet import git

URL_TEMPLATE = 'https://{}github.com/slarse/clanim'

CloneFixtureData = namedtuple('CloneFixtureData', ['expected_url'])


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


def test_clone_raises_on_type_errors():
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


@pytest.fixture(scope='function')
def clone(mocker, monkeypatch):
    token = 'besttoken1337'
    monkeypatch.setattr('gits_pet.git.OAUTH_TOKEN', token)
    mocker.patch(
        'gits_pet.git.captured_run', autospec=True, return_value=(0, b'', b''))
    expected_url = URL_TEMPLATE.format(token + '@')
    return CloneFixtureData(expected_url=expected_url)


def test_clone_issues_correct_command_with_defaults(clone):
    expected_command = "git clone {} --single-branch".format(
        clone.expected_url).split()

    git.clone(URL_TEMPLATE.format(''))
    git.captured_run.assert_called_once_with(expected_command)


def test_clone_issues_correct_command_without_single_branch(clone):
    expected_command = "git clone {}".format(clone.expected_url).split()

    git.clone(URL_TEMPLATE.format(''), single_branch=False)
    git.captured_run.assert_called_once_with(expected_command)


def test_clone_issues_correct_command_with_single_other_branch(clone):
    branch = 'other-branch'
    expected_command = "git clone {} --single-branch -b {}".format(
        clone.expected_url, branch).split()

    git.clone(URL_TEMPLATE.format(''), single_branch=True, branch=branch)
    git.captured_run.assert_called_once_with(expected_command)


def test_clone_raises_on_non_zero_exit_from_git_clone(clone, mocker):
    stderr = b'This is pretty bad!'
    # already patched in clone fixture
    git.captured_run.return_value = (1, b'', stderr)

    with pytest.raises(git.CloneFailedError) as exc:
        git.clone("{}".format(URL_TEMPLATE.format('')))
    assert stderr.decode(
        encoding=sys.getdefaultencoding()) in str(exc.value)
