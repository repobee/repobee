"""Test setup."""
import sys
import pathlib
import pytest
import tempfile
import string
import os
from unittest.mock import patch, MagicMock

# the git module must be imported with a mocked env variable
TOKEN = 'besttoken1337'
with patch('os.getenv', autospec=True, return_value=TOKEN):
    import gits_pet
    from gits_pet import git

from gits_pet import tuples

# mock the PyGithub github module
sys.modules['github'] = MagicMock()

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
    functions = dict(GENERATE_REPO_URL=GENERATE_REPO_URL)
    return dict(constants=constants, functions=functions)


@pytest.fixture
def config_mock(mocker, isfile_mock, students_file):
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(
                mode="w",
                encoding=sys.getdefaultencoding(),
                dir=tmpdir,
                delete=False) as file:
            isfile = isfile_mock.side_effect
            isfile_mock.side_effect = lambda path: isfile(path) or str(path) == file.name
            file.write(
                os.linesep.join([
                    "[DEFAULTS]",
                    "github_base_url = {}".format(GITHUB_BASE_URL),
                    "user = {}".format(USER), "org_name = {}".format(ORG_NAME),
                    "students_file = {}".format(students_file.name)
                ]))
            file.flush()

        read_config = gits_pet.config._read_config
        mocker.patch(
            'gits_pet.config._read_config',
            side_effect=lambda _: read_config(pathlib.Path(file.name)))
        yield file
