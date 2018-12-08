"""Test setup."""
import sys
import pathlib
import pytest
from collections import namedtuple
from datetime import datetime, timedelta
import random
from contextlib import contextmanager
import tempfile
import string
import os
from unittest.mock import patch, MagicMock

random.seed(41235)

# mock the PyGithub github module
sys.modules['github'] = MagicMock()


import repomate

from repomate import tuples
from repomate import config

USER = 'slarse'
ORG_NAME = 'test-org'
MASTER_ORG_NAME = 'test-master-org'
HOST_URL = 'https://some_enterprise_host'
GITHUB_BASE_URL = '{}/api/v3'.format(HOST_URL)
STUDENTS = tuple(string.ascii_lowercase[:4])
ISSUE_PATH = 'some/issue/path'
ISSUE = tuples.Issue(title="Best title", body="This is the body of the issue.")
PLUGINS = ['javac', 'pylint']
TOKEN = 'besttoken1337'
CONFIG_TOKEN = 'bestconfigtoken'


GENERATE_REPO_URL = lambda repo_name, org_name:\
        "{}/{}/{}".format(HOST_URL, org_name, repo_name)

User = namedtuple('User', ('login', ))


def pytest_namespace():
    constants = dict(
        USER=USER,
        HOST_URL=HOST_URL,
        GITHUB_BASE_URL=GITHUB_BASE_URL,
        ORG_NAME=ORG_NAME,
        MASTER_ORG_NAME=MASTER_ORG_NAME,
        STUDENTS=STUDENTS,
        ISSUE_PATH=ISSUE_PATH,
        ISSUE=ISSUE,
        PLUGINS=PLUGINS,
        TOKEN=TOKEN,
        CONFIG_TOKEN=CONFIG_TOKEN,
    )
    functions = dict(
        GENERATE_REPO_URL=GENERATE_REPO_URL,
        raise_=raise_,
        to_magic_mock_issue=to_magic_mock_issue,
        from_magic_mock_issue=from_magic_mock_issue,
        RANDOM_DATE=RANDOM_DATE)
    classes = dict(User=User)
    return dict(constants=constants, functions=functions, classes=classes)


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

@pytest.fixture(autouse=True)
def mock_getenv(mocker):
    def _side_effect(name):
        if name != 'REPOMATE_OAUTH':
            raise ValueError("no such environment variable")
        return TOKEN
    mock = mocker.patch('os.getenv', side_effect=_side_effect)
    return mock

@pytest.fixture
def plugin_manager_mock(mocker):
    return mocker.patch('repomate_plug.manager', autospec=True)


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
    isfile = lambda path: str(path) != str(config.DEFAULT_CONFIG_FILE) and os.path.isfile(str(path))
    return mocker.patch(
        'pathlib.Path.is_file', autospec=True, side_effect=isfile)


@pytest.fixture(autouse=True)
def no_config_mock(mocker, isfile_mock, tmpdir):
    """Mock which ensures that no config file is found."""
    isfile = isfile_mock.side_effect
    isfile_mock.side_effect = \
        lambda path: path != config.DEFAULT_CONFIG_FILE and isfile(path)


@pytest.fixture
def empty_config_mock(mocker, isfile_mock, tmpdir):
    """Sets up an empty config file which is read by the config._read_config
    function."""
    file = tmpdir.join('config.cnf')
    file.ensure()
    read_config = repomate.config._read_config
    mocker.patch(
        'repomate.config._read_config',
        side_effect=lambda _: read_config(pathlib.Path(str(file))))
    read_defaults = repomate.config._read_defaults
    mocker.patch(
        'repomate.config._read_defaults',
        side_effect=lambda _: read_defaults(pathlib.Path(str(file))))
    isfile = isfile_mock.side_effect
    isfile_mock.side_effect = lambda path: isfile(path) or str(path) == str(file)
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
_config_master_org = "master_org_name = {}".format(MASTER_ORG_NAME)


@pytest.fixture(params=['-g', '-u', '-sf', '-o', '-mo'])
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
    if not missing_option == '-mo':
        config_contents.append(_config_master_org)

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
        "master_org_name = {}".format(MASTER_ORG_NAME),
        "students_file = {!s}".format(students_file),
        "plugins = {!s}".format(','.join(PLUGINS)),
        "token = {}".format(CONFIG_TOKEN),
    ])
    empty_config_mock.write(config_contents)
    yield empty_config_mock


def to_magic_mock_issue(issue):
    """Convert an issue to a MagicMock with all of the correct
    attribuets."""
    mock = MagicMock()
    mock.user = MagicMock()
    mock.title = issue.title
    mock.body = issue.body
    mock.created_at = issue.created_at
    mock.number = issue.number
    mock.user = User(issue.author)
    return mock


def from_magic_mock_issue(mock_issue):
    """Convert a MagicMock issue into a tuples.Issue."""
    return tuples.Issue(
        title=mock_issue.title,
        body=mock_issue.body,
        number=mock_issue.number,
        created_at=mock_issue.created_at,
        author=mock_issue.user.login)


FIXED_DATETIME = datetime(2009, 11, 22)
RANDOM_DATE = lambda: \
        (FIXED_DATETIME -
         timedelta(
             days=random.randint(0, 1000),
             hours=random.randint(0, 1000),
             minutes=random.randint(0, 1000),
             seconds=random.randint(0, 1000))
        )
