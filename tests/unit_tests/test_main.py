import argparse
from unittest.mock import MagicMock
from collections import namedtuple

import pytest

from functions import raise_
from _repobee import cli
from _repobee import main
from _repobee import plugin

import constants

ORG_NAME = constants.ORG_NAME
BASE_URL = constants.BASE_URL
USER = constants.USER

VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    base_url=BASE_URL,
    user=USER,
    master_repo_urls="url-1 url-2 url-3".split(),
    master_repo_names="1 2 3".split(),
    students=constants.STUDENTS,
    issue=constants.ISSUE,
    title_regex="some regex",
    traceback=False,
)

PARSED_ARGS = argparse.Namespace(
    subparser=cli.SETUP_PARSER, **VALID_PARSED_ARGS
)

CLONE_ARGS = "clone -mn week-2 -s slarse".split()

module = namedtuple("module", ("name",))


@pytest.fixture
def logger_exception_mock(mocker):
    return mocker.patch("_repobee.main.LOGGER.exception", autospec=True)


@pytest.fixture
def api_instance_mock(mocker):
    return MagicMock(spec="_repobee.github.GitHubAPI")


@pytest.fixture
def init_plugins_mock(mocker):
    def init_plugins(plugs=None):
        list(map(module, plugs or []))

    return mocker.patch(
        "_repobee.plugin.initialize_plugins",
        autospec=True,
        side_effect=init_plugins,
    )


@pytest.fixture
def parse_args_mock(mocker, api_instance_mock):
    return mocker.patch(
        "_repobee.cli.parse_args",
        autospec=True,
        return_value=(PARSED_ARGS, api_instance_mock),
    )


@pytest.fixture
def parse_preparser_options_mock(mocker):
    return mocker.patch("_repobee.cli.parse_preparser_options", autospec=True)


@pytest.fixture
def dispatch_command_mock(mocker):
    return mocker.patch("_repobee.cli.dispatch_command", autospec=True)


def test_happy_path(
    api_instance_mock, parse_args_mock, dispatch_command_mock, no_config_mock
):

    sys_args = ["just some made up arguments".split()]

    main.main(sys_args)

    parse_args_mock.assert_called_once_with(sys_args[1:], show_all_opts=False)
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

    parse_args_mock.assert_called_once_with(sys_args[1:], show_all_opts=False)
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
    parse_args_mock.assert_called_once_with(CLONE_ARGS, show_all_opts=False)


def test_no_plugins_arg(
    parse_args_mock, dispatch_command_mock, init_plugins_mock
):
    """Default plugins still need to be loaded, so initialize_plugins should be
    called without arguments.
    """
    sys_args = ["repobee", "--no-plugins", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with()
    parse_args_mock.assert_called_once_with(CLONE_ARGS, show_all_opts=False)


def test_plugin_with_subparser_name(
    parse_args_mock, dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "-p", "javac", "-p", "clone", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with(["javac", "clone"])
    parse_args_mock.assert_called_once_with(CLONE_ARGS, show_all_opts=False)


def test_plug_arg_incompatible_with_no_plugins(
    dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "-p", "javac", "--no-plugins", *CLONE_ARGS]

    with pytest.raises(SystemExit):
        main.main(sys_args)

    assert not init_plugins_mock.called
    assert not dispatch_command_mock.called


def test_invalid_plug_options(dispatch_command_mock, init_plugins_mock):
    """-f is not a valid option for plugins and should be bumped to the
    main parser

    Note that the default plugins must be loaded for this test to work.
    """
    # load default plugins
    loaded = plugin.load_plugin_modules()
    print(loaded)
    plugin.register_plugins(loaded)

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
    args_with_traceback = dict(VALID_PARSED_ARGS)
    args_with_traceback["traceback"] = True
    parsed_args = argparse.Namespace(**args_with_traceback)
    parse_args_mock.return_value = parsed_args, api_instance_mock

    def raise_():
        raise ValueError(msg)

    sys_args = ["repobee", *CLONE_ARGS, "--traceback"]
    dispatch_command_mock.side_effect = lambda *args, **kwargs: raise_()

    main.main(sys_args)

    assert logger_exception_mock.called
    parse_args_mock.assert_called_once_with(
        [*CLONE_ARGS, "--traceback"], show_all_opts=False
    )


def test_show_all_opts_correctly_separated(
    parse_args_mock, parse_preparser_options_mock, no_config_mock
):
    msg = "expected exit"

    def _raise_sysexit(*args, **kwargs):
        raise SystemExit(msg)

    parse_preparser_options_mock.return_value = argparse.Namespace(
        show_all_opts=True, no_plugins=False, plug=None
    )
    parse_args_mock.side_effect = _raise_sysexit
    sys_args = [
        "repobee",
        cli.PRE_PARSER_SHOW_ALL_OPTS,
        cli.SETUP_PARSER,
        "-h",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert msg in str(exc_info.value)
    parse_args_mock.assert_called_once_with(
        [cli.SETUP_PARSER, "-h"], show_all_opts=True
    )
    parse_preparser_options_mock.assert_called_once_with(
        [cli.PRE_PARSER_SHOW_ALL_OPTS]
    )
