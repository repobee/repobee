from unittest.mock import MagicMock
from collections import namedtuple

import pytest

from functions import raise_
from repobee import cli
from repobee import main
from repobee import tuples

import constants

ORG_NAME = constants.ORG_NAME
GITHUB_BASE_URL = constants.GITHUB_BASE_URL
USER = constants.USER

VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    base_url=GITHUB_BASE_URL,
    user=USER,
    master_repo_urls="url-1 url-2 url-3".split(),
    master_repo_names="1 2 3".split(),
    students=constants.STUDENTS,
    issue=constants.ISSUE,
    title_regex="some regex",
)

PARSED_ARGS = tuples.Args(cli.SETUP_PARSER, **VALID_PARSED_ARGS)

CLONE_ARGS = "clone -mn week-2 -s slarse".split()

module = namedtuple("module", ("name",))


@pytest.fixture(autouse=True)
def register_plugins_mock(mocker):
    """As initialize_plugins is called multiple times, we need to mock out the
    register_plugins method. Otherwise, it raises when trying to load the same
    plugin twice.
    """
    return mocker.patch("repobee.plugin.register_plugins", autospec=True)


@pytest.fixture
def logger_exception_mock(mocker):
    return mocker.patch("repobee.main.LOGGER.exception", autospec=True)


@pytest.fixture
def api_instance_mock(mocker):
    return MagicMock(spec="repobee.github_api.GitHubAPI")


@pytest.fixture
def init_plugins_mock(mocker):
    return mocker.patch(
        "repobee.plugin.initialize_plugins",
        autospec=True,
        side_effect=lambda plugs: list(map(module, plugs)),
    )


@pytest.fixture
def parse_args_mock(mocker, api_instance_mock):
    return mocker.patch(
        "repobee.cli.parse_args",
        autospec=True,
        return_value=(PARSED_ARGS, api_instance_mock),
    )


@pytest.fixture
def parse_plugins_mock(mocker):
    return mocker.patch(
        "repobee.cli.parse_plugins",
        autospec=True,
        side_effect=lambda args: [
            arg for arg in args if not arg.startswith("-")
        ],
    )


@pytest.fixture
def dispatch_command_mock(mocker):
    return mocker.patch("repobee.cli.dispatch_command", autospec=True)


def test_happy_path(
    api_instance_mock, parse_args_mock, dispatch_command_mock, no_config_mock
):

    sys_args = ["just some made up arguments".split()]

    main.main(sys_args)

    parse_args_mock.assert_called_once_with(sys_args[1:])
    dispatch_command_mock.assert_called_once_with(
        PARSED_ARGS, api_instance_mock
    )


def test_does_not_raise_on_exception_in_parsing(
    api_instance_mock, parse_args_mock, dispatch_command_mock, no_config_mock
):
    """should just log, but not raise."""
    msg = "some nice error message"
    parse_args_mock.side_effect = raise_(Exception(msg))
    sys_args = ["just some made up arguments".split()]

    main.main(sys_args)

    parse_args_mock.assert_called_once_with(sys_args[1:])
    assert not dispatch_command_mock.called


def test_does_not_raise_on_exception_in_handling_parsed_args(
    api_instance_mock, parse_args_mock, dispatch_command_mock
):
    """should just log, but not raise."""
    msg = "some nice error message"
    dispatch_command_mock.side_effect = raise_(Exception(msg))
    sys_args = ["just some made up arguments".split()]

    main.main(sys_args)


def test_plugins_args(
    parse_args_mock, dispatch_command_mock, init_plugins_mock
):
    plugin_args = "-p javac -p pylint".split()
    sys_args = ["repobee", *plugin_args, *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with(["javac", "pylint"])
    parse_args_mock.assert_called_once_with(CLONE_ARGS)


def test_no_plugins_arg(
    parse_args_mock, dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "--no-plugins", *CLONE_ARGS]

    main.main(sys_args)

    assert not init_plugins_mock.called
    parse_args_mock.assert_called_once_with(CLONE_ARGS)


def test_plugin_with_subparser_name(
    parse_args_mock, dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "-p", "javac", "-p", "clone", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with(["javac", "clone"])
    parse_args_mock.assert_called_once_with(CLONE_ARGS)


def test_plug_arg_incompatible_with_no_plugins(
    dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "-p", "javac", "--no-plugins", *CLONE_ARGS]

    with pytest.raises(SystemExit):
        main.main(sys_args)

    assert not init_plugins_mock.called
    assert not dispatch_command_mock.called


def test_invalid_plug_options(dispatch_command_mock, init_plugins_mock):
    # -f is not a valid option for plugins and should be bumped to the
    # main parser
    sys_args = ["repobee", "-p", "javac", "-f", *CLONE_ARGS]

    with pytest.raises(SystemExit):
        main.main(sys_args)

    init_plugins_mock.assert_called_once_with(["javac"])
    assert not dispatch_command_mock.called


def test_does_not_raise_on_exception_in_dispatch(
    api_instance_mock,
    parse_args_mock,
    dispatch_command_mock,
    no_config_mock,
    logger_exception_mock,
):
    sys_args = ["repobee", *CLONE_ARGS]
    main.main(sys_args)

    assert not logger_exception_mock.called


def test_logs_traceback_on_exception_in_dispatch_if_traceback(
    api_instance_mock,
    parse_args_mock,
    dispatch_command_mock,
    no_config_mock,
    logger_exception_mock,
):
    msg = "oh this is bad!!"
    parsed_args = tuples.Args(**VALID_PARSED_ARGS, traceback=True)
    parse_args_mock.return_value = parsed_args, api_instance_mock

    def raise_():
        raise ValueError(msg)

    sys_args = ["repobee", *CLONE_ARGS, "--traceback"]
    dispatch_command_mock.side_effect = lambda *args, **kwargs: raise_()

    main.main(sys_args)

    assert logger_exception_mock.called
    parse_args_mock.assert_called_once_with([*CLONE_ARGS, "--traceback"])
