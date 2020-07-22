"""Test setup."""
import sys
import pathlib
import tempfile
from contextlib import contextmanager
import os
from unittest.mock import MagicMock
import pytest

import _repobee.constants
import _repobee.config
import _repobee.plugin

import constants

# mock the PyGithub github module
sys.modules["github"] = MagicMock()


import _repobee  # noqa: E402

EXPECTED_ENV_VARIABLES = [
    _repobee.constants.TOKEN_ENV,
    "REPOBEE_NO_VERIFY_SSL",
]


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
            delete=False,
        ) as file:
            if populate:
                file.writelines(
                    "{}{}".format(student, os.linesep)
                    for student in constants.STUDENTS
                )
                file.flush()
        yield file


@pytest.fixture
def unused_path():
    with tempfile.NamedTemporaryFile() as tmpfile:
        unused_path = pathlib.Path(tmpfile.name)

    # exiting the with block destroys the temporary file
    return unused_path


@pytest.fixture(autouse=True)
def unregister_plugins():
    """All plugins should be unregistered after each function."""
    _repobee.plugin.unregister_all_plugins()


@pytest.fixture(autouse=True)
def mock_getenv(mocker):
    def _side_effect(name):
        if name not in EXPECTED_ENV_VARIABLES:
            raise ValueError("no such environment variable")
        return constants.TOKEN

    mock = mocker.patch("os.getenv", side_effect=_side_effect)
    return mock


@pytest.fixture
def plugin_manager_mock(mocker):
    return mocker.patch("repobee_plug.manager", autospec=True)


@pytest.fixture
def empty_students_file(mocker, tmpdir):
    """Fixture with an empty temporary file."""
    file = tmpdir.join("students")
    file.ensure()
    yield file


@pytest.fixture
def students_file(empty_students_file):
    """A fixture with a temporary file containt the students in
    constants.STUDENTS.
    """
    empty_students_file.write(
        os.linesep.join([str(s) for s in constants.STUDENTS])
    )
    yield empty_students_file


@pytest.fixture
def isfile_mock(request, mocker):
    """Mocks pathlib.Path.is_file to only return true if the path does not
    point to the default configuration file.
    """
    if "noisfilemock" in request.keywords:
        return

    def isfile(path):
        return str(path) != str(
            _repobee.constants.DEFAULT_CONFIG_FILE
        ) and os.path.isfile(str(path))

    return mocker.patch(
        "pathlib.Path.is_file", autospec=True, side_effect=isfile
    )


@pytest.fixture(autouse=True)
def no_config_mock(mocker, isfile_mock, tmpdir):
    """Mock which ensures that no config file is found."""
    isfile = isfile_mock.side_effect
    isfile_mock.side_effect = (
        lambda path: path != _repobee.constants.DEFAULT_CONFIG_FILE
        and isfile(path)
    )


@pytest.fixture
def empty_config_mock(mocker, isfile_mock, tmpdir, monkeypatch):
    """Sets up an empty config file which is read by the config._read_config
    function."""
    file = tmpdir.join("config.ini")
    file.ensure()
    read_config = _repobee.config._read_config
    mocker.patch(
        "_repobee.config._read_config",
        side_effect=lambda _: read_config(pathlib.Path(str(file))),
    )
    read_defaults = _repobee.config._read_defaults
    mocker.patch(
        "_repobee.config._read_defaults",
        side_effect=lambda _: read_defaults(pathlib.Path(str(file))),
    )
    isfile = isfile_mock.side_effect
    isfile_mock.side_effect = lambda path: isfile(path) or str(path) == str(
        file
    )
    monkeypatch.setattr(
        "_repobee.constants.DEFAULT_CONFIG_FILE", pathlib.Path(str(file))
    )
    yield file


_config_user = "user = {}".format(constants.USER)
_config_base = "base_url = {}".format(constants.BASE_URL)
_config_org = "org_name = {}".format(constants.ORG_NAME)
_config_master_org = "master_org_name = {}".format(constants.MASTER_ORG_NAME)


@pytest.fixture(params=["--bu", "-u", "--sf", "-o", "--mo"])
def config_missing_option(request, empty_config_mock, students_file):
    missing_option = request.param

    config_contents = ["[DEFAULTS]"]
    if not missing_option == "--bu":
        config_contents.append(_config_base)
    if not missing_option == "-o":
        config_contents.append(_config_org)
    if not missing_option == "--sf":
        config_contents.append("students_file = {!s}".format(students_file))
    if not missing_option == "-u":
        config_contents.append(_config_user)
    if not missing_option == "--mo":
        config_contents.append(_config_master_org)

    empty_config_mock.write(os.linesep.join(config_contents))

    yield missing_option


@pytest.fixture
def config_mock(empty_config_mock, students_file):
    """Fixture with a pre-filled config file."""
    config_contents = os.linesep.join(
        [
            "[DEFAULTS]",
            "base_url = {}".format(constants.BASE_URL),
            "user = {}".format(constants.USER),
            "org_name = {}".format(constants.ORG_NAME),
            "master_org_name = {}".format(constants.MASTER_ORG_NAME),
            "students_file = {!s}".format(students_file),
            "plugins = {!s}".format(",".join(constants.PLUGINS)),
            "token = {}".format(constants.CONFIG_TOKEN),
        ]
    )
    empty_config_mock.write(config_contents)
    yield empty_config_mock


@pytest.fixture
def load_default_plugins():
    """Load the default plugins."""
    default_plugin_names = _repobee.plugin.get_qualified_module_names(
        _repobee.ext.defaults
    )
    _repobee.plugin.initialize_plugins(
        default_plugin_names, allow_qualified=True
    )
