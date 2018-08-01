"""Test setup."""
import sys
import pathlib
import pytest
from contextlib import contextmanager
import tempfile
import string
import os
from unittest.mock import patch, MagicMock

# mock the PyGithub github module
sys.modules['github'] = MagicMock()

# assert that importing git without oauth env raises OSError
with patch('os.getenv', autospec=True, return_value=""):
    with pytest.raises(OSError):
        from gits_pet import git

# the git module must be imported with a mocked env variable
TOKEN = 'besttoken1337'
with patch('os.getenv', autospec=True, return_value=TOKEN):
    import gits_pet
    from gits_pet import git

from gits_pet import tuples
from gits_pet import config

assert TOKEN == gits_pet.git.OAUTH_TOKEN

USER = 'slarse'
ORG_NAME = 'test-org'
GITHUB_BASE_URL = 'https://some_enterprise_host/api/v3'
STUDENTS = tuple(string.ascii_lowercase)
ISSUE_PATH = 'some/issue/path'
ISSUE = tuples.Issue(title="Best title", body="This is the body of the issue.")


GENERATE_REPO_URL = lambda repo_name:\
        "https://some_enterprise_host/{}/{}".format(ORG_NAME, repo_name)


def pytest_namespace():
    constants = dict(
        USER=USER,
        GITHUB_BASE_URL=GITHUB_BASE_URL,
        ORG_NAME=ORG_NAME,
        STUDENTS=STUDENTS,
        ISSUE_PATH=ISSUE_PATH,
        ISSUE=ISSUE)
    functions = dict(GENERATE_REPO_URL=GENERATE_REPO_URL, raise_=raise_)
    return dict(constants=constants, functions=functions)


@contextmanager
def _students_file(populate: bool = True):
    """A contextmanager that yields a student file. The file is populated
    with the STUDENTS tuple by default, with one element on each line.

    Args:
        populate: If true, the file is populated with the students in the
        STUDENTS tuple.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(
                mode="w",
                encoding=sys.getdefaultencoding(),
                dir=tmpdir,
                delete=False) as file:
            if populate:
                file.writelines(
                    "{}{}".format(student, os.linesep) for student in STUDENTS)
                file.flush()
        yield file


@pytest.fixture
def empty_students_file(mocker, tmpdir):
    """Fixture with an empty temporary file."""
    file = tmpdir.join("students")
    file.ensure()
    yield file


@pytest.fixture
def students_file(empty_students_file):
    """A fixture with a temporary file containt the students in
    pytest.constants.STUDENTS.
    """
    empty_students_file.write(os.linesep.join(STUDENTS))
    yield empty_students_file


@pytest.fixture
def isfile_mock(request, mocker):
    """Mocks pathlib.Path.is_file to only return true if the path does not
    point to the default configuration file.
    """
    if 'noisfilemock' in request.keywords:
        return
    isfile = lambda path: path != config.DEFAULT_CONFIG_FILE
    return mocker.patch(
        'pathlib.Path.is_file', autospec=True, side_effect=isfile)


@pytest.fixture
def empty_config_mock(mocker, isfile_mock, tmpdir):
    """Sets up an empty config file which is read by the config._read_config
    function."""
    file = tmpdir.join('config.cnf')
    file.ensure()
    read_config = gits_pet.config._read_config
    mocker.patch(
        'gits_pet.config._read_config',
        side_effect=lambda _: read_config(pathlib.Path(str(file))))
    isfile = isfile_mock.side_effect
    isfile_mock.side_effect = lambda path: isfile(path) or str(path) == file.name
    yield file


def raise_(exception):
    """Function meant for raising exceptions in lambda.

    Args:
        exception: An exception to raise (initialized object, not class)
    Returns:
        A function that raises the provided exception when called with any
        arguments.
    Usage:
        something = lambda: raise_(ValueError('bad value'))
    """

    def raise_exception(*args, **kwargs):
        raise exception

    return raise_exception


_config_user = "user = {}".format(USER)
_config_base = "github_base_url = {}".format(GITHUB_BASE_URL)
_config_org = "org_name = {}".format(ORG_NAME)


@pytest.fixture(params=['-g', '-u', '-sf', '-o'])
def config_missing_option(request, empty_config_mock, students_file):
    missing_option = request.param

    config_contents = ["[DEFAULTS]"]
    if not missing_option == '-g':
        config_contents.append(_config_base)
    if not missing_option == '-o':
        config_contents.append(_config_org)
    if not missing_option == '-sf':
        config_contents.append("students_file = {!s}".format(students_file))
    if not missing_option == '-u':
        config_contents.append(_config_user)

    empty_config_mock.write(os.linesep.join(config_contents))

    yield missing_option


@pytest.fixture
def config_mock(empty_config_mock, students_file):
    """Fixture with a pre-filled config file."""
    config_contents = os.linesep.join([
        "[DEFAULTS]",
        "github_base_url = {}".format(GITHUB_BASE_URL),
        "user = {}".format(USER),
        "org_name = {}".format(ORG_NAME),
        "students_file = {!s}".format(students_file),
    ])
    empty_config_mock.write(config_contents)
    yield empty_config_mock
