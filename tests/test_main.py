from unittest.mock import patch, MagicMock
import builtins
import pytest

from pytest.functions import raise_
import repomate
from repomate import cli
from repomate import main
from repomate import tuples

ORG_NAME = pytest.constants.ORG_NAME
GITHUB_BASE_URL = pytest.constants.GITHUB_BASE_URL
USER = pytest.constants.USER

VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    github_base_url=GITHUB_BASE_URL,
    user=USER,
    master_repo_urls="url-1 url-2 url-3".split(),
    master_repo_names="1 2 3".split(),
    students=pytest.constants.STUDENTS,
    issue=pytest.constants.ISSUE,
    title_regex="some regex")

PARSED_ARGS = tuples.Args(cli.SETUP_PARSER, **VALID_PARSED_ARGS)


@pytest.fixture
def monkeypatch_sys_args(monkeypatch):
    sys_args = ['just some made up arguments'.split()]
    monkeypatch.setattr('sys.argv', sys_args)
    return sys_args


@pytest.fixture
def api_instance_mock(mocker):
    return MagicMock(spec='repomate.APIWrapper')


@pytest.fixture
def parse_args_mock(mocker, api_instance_mock):
    return mocker.patch(
        'repomate.cli.parse_args',
        autospec=True,
        return_value=(PARSED_ARGS, api_instance_mock))


@pytest.fixture
def dispatch_command_mock(mocker):
    return mocker.patch('repomate.cli.dispatch_command', autospec=True)


def test_happy_path(monkeypatch_sys_args, api_instance_mock, parse_args_mock,
                    dispatch_command_mock):
    main.main()

    parse_args_mock.assert_called_once_with(monkeypatch_sys_args[1:])
    dispatch_command_mock.assert_called_once_with(PARSED_ARGS,
                                                    api_instance_mock)


def test_does_not_raise_on_exception_in_parsing(
        monkeypatch_sys_args, api_instance_mock, parse_args_mock,
        dispatch_command_mock):
    """should just log, but not raise."""
    msg = "some nice error message"
    parse_args_mock.side_effect = raise_(Exception(msg))

    main.main()

    parse_args_mock.assert_called_once_with(monkeypatch_sys_args[1:])
    assert not dispatch_command_mock.called


def test_does_not_raise_on_exception_in_handling_parsed_args(
        monkeypatch_sys_args, api_instance_mock, parse_args_mock,
        dispatch_command_mock):
    """should just log, but not raise."""
    msg = "some nice error message"
    dispatch_command_mock.side_effect = raise_(Exception(msg))

    main.main()
