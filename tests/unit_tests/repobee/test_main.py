import os
import argparse
import tempfile
import pathlib
import types
from unittest.mock import MagicMock, patch, call
from collections import namedtuple

import pytest

import repobee_plug as plug

import _repobee.cli.preparser
import _repobee.ext.defaults
import _repobee.ext.dist
from functions import raise_
import _repobee.constants
import repobee_plug.cli
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
    **repobee_plug.cli.CoreCommand.repos.setup.asdict(), **VALID_PARSED_ARGS
)

CLONE_ARGS = "clone --mn week-2 -s slarse".split()

module = namedtuple("module", ("name",))

DEFAULT_PLUGIN_NAMES = plugin.get_qualified_module_names(_repobee.ext.defaults)


@pytest.fixture
def logger_exception_mock(mocker):
    return mocker.patch("_repobee.main.LOGGER.exception", autospec=True)


@pytest.fixture
def api_instance_mock(mocker):
    return MagicMock(spec="_repobee.github.GitHubAPI")


@pytest.fixture
def init_plugins_mock(mocker):
    def init_plugins(plugs=None, allow_qualified=False, allow_filepath=False):
        list(map(module, plugs or []))

    return mocker.patch(
        "_repobee.plugin.initialize_plugins",
        autospec=True,
        side_effect=init_plugins,
    )


@pytest.fixture
def handle_args_mock(mocker, api_instance_mock):
    return mocker.patch(
        "_repobee.cli.parsing.handle_args",
        autospec=True,
        return_value=(PARSED_ARGS, api_instance_mock),
    )


@pytest.fixture
def parse_preparser_options_mock(mocker):
    return mocker.patch("_repobee.cli.preparser.parse_args", autospec=True)


@pytest.fixture
def dispatch_command_mock(mocker):
    return mocker.patch(
        "_repobee.cli.dispatch.dispatch_command", autospec=True
    )


def test_happy_path(
    api_instance_mock, handle_args_mock, dispatch_command_mock, no_config_mock
):
    sys_args = ["just some made up arguments".split()]

    main.main(sys_args)

    handle_args_mock.assert_called_once_with(
        sys_args[1:],
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )
    dispatch_command_mock.assert_called_once_with(
        PARSED_ARGS, api_instance_mock, _repobee.constants.DEFAULT_CONFIG_FILE
    )


def test_exit_status_1_on_exception_in_parsing(
    api_instance_mock, handle_args_mock, dispatch_command_mock, no_config_mock
):
    msg = "some nice error message"
    handle_args_mock.side_effect = raise_(Exception(msg))
    sys_args = ["just some made up arguments".split()]

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert exc_info.value.code == 1
    handle_args_mock.assert_called_once_with(
        sys_args[1:],
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )
    assert not dispatch_command_mock.called


def test_exit_status_1_on_exception_in_handling_parsed_args(
    api_instance_mock, handle_args_mock, dispatch_command_mock
):
    """should just log, but not raise."""
    msg = "some nice error message"
    dispatch_command_mock.side_effect = raise_(Exception(msg))
    sys_args = ["just some made up arguments".split()]

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert exc_info.value.code == 1
    handle_args_mock.assert_called_once_with(
        sys_args[1:],
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_plugins_args(
    handle_args_mock, dispatch_command_mock, init_plugins_mock
):
    plugin_args = "-p javac -p pylint".split()
    sys_args = ["repobee", *plugin_args, *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_has_calls(
        [
            call(["javac", "pylint"], allow_filepath=True),
            call(DEFAULT_PLUGIN_NAMES, allow_qualified=True),
        ],
        any_order=True,
    )
    handle_args_mock.assert_called_once_with(
        CLONE_ARGS,
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_no_plugins_arg(
    handle_args_mock, dispatch_command_mock, init_plugins_mock
):
    """Default plugins still need to be loaded, so initialize_plugins should be
    called only with the default plugin.
    """
    sys_args = ["repobee", "--no-plugins", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with(
        DEFAULT_PLUGIN_NAMES, allow_qualified=True
    )
    handle_args_mock.assert_called_once_with(
        CLONE_ARGS,
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_no_plugins_with_configured_plugins(
    handle_args_mock, dispatch_command_mock, init_plugins_mock, config_mock
):
    """Test that --no-plugins causes any plugins listed in the config file to
    NOT be loaded.
    """
    sys_args = ["repobee", "--no-plugins", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_called_once_with(
        DEFAULT_PLUGIN_NAMES, allow_qualified=True
    )
    handle_args_mock.assert_called_once_with(
        CLONE_ARGS,
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_configured_plugins_are_loaded(
    handle_args_mock, dispatch_command_mock, init_plugins_mock, config_mock
):
    sys_args = ["repobee", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_has_calls(
        [
            call(["javac", "pylint"], allow_filepath=True),
            call(DEFAULT_PLUGIN_NAMES, allow_qualified=True),
        ],
        any_order=True,
    )
    handle_args_mock.assert_called_once_with(
        CLONE_ARGS,
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_dist_plugins_are_loaded_when_dist_install(monkeypatch):
    dist_plugin_qualnames = plugin.get_qualified_module_names(
        _repobee.ext.dist
    )
    sys_args = "repobee -h".split()
    monkeypatch.setattr("_repobee.distinfo.DIST_INSTALL", True)

    with pytest.raises(SystemExit):
        # calling -h always causes a SystemExit
        main.main(sys_args, unload_plugins=False)

    qualnames = {
        p.__name__
        for p in plug.manager.get_plugins()
        if isinstance(p, types.ModuleType)
    }

    assert qualnames.issuperset(dist_plugin_qualnames)


def test_plugin_with_subparser_name(
    handle_args_mock, dispatch_command_mock, init_plugins_mock
):
    sys_args = ["repobee", "-p", "javac", "-p", "clone", *CLONE_ARGS]

    main.main(sys_args)

    init_plugins_mock.assert_has_calls(
        [
            call(["javac", "clone"], allow_filepath=True),
            call(DEFAULT_PLUGIN_NAMES, allow_qualified=True),
        ],
        any_order=True,
    )
    handle_args_mock.assert_called_once_with(
        CLONE_ARGS,
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


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
    plugin.initialize_plugins(
        plugin.get_qualified_module_names(_repobee.ext.defaults),
        allow_qualified=True,
    )

    sys_args = ["repobee", "-p", "javac", "-f", *CLONE_ARGS]

    with pytest.raises(SystemExit):
        main.main(sys_args)

    init_plugins_mock.assert_has_calls(
        [
            call(["javac"], allow_filepath=True),
            call(DEFAULT_PLUGIN_NAMES, allow_qualified=True),
        ],
        any_order=True,
    )
    assert not dispatch_command_mock.called


def test_does_not_raise_on_exception_in_dispatch(
    api_instance_mock,
    handle_args_mock,
    dispatch_command_mock,
    no_config_mock,
    logger_exception_mock,
):
    sys_args = ["repobee", *CLONE_ARGS]
    main.main(sys_args)

    assert not logger_exception_mock.called


def test_logs_traceback_on_exception_in_dispatch_if_traceback(
    api_instance_mock,
    handle_args_mock,
    dispatch_command_mock,
    no_config_mock,
    logger_exception_mock,
):
    msg = "oh this is bad!!"
    args_with_traceback = dict(VALID_PARSED_ARGS)
    args_with_traceback["traceback"] = True
    parsed_args = argparse.Namespace(**args_with_traceback)
    handle_args_mock.return_value = parsed_args, api_instance_mock

    def raise_():
        raise ValueError(msg)

    sys_args = ["repobee", *CLONE_ARGS, "--traceback"]
    dispatch_command_mock.side_effect = lambda *args, **kwargs: raise_()

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert exc_info.value.code == 1
    assert logger_exception_mock.called
    handle_args_mock.assert_called_once_with(
        [*CLONE_ARGS, "--traceback"],
        show_all_opts=False,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def test_show_all_opts_correctly_separated(
    handle_args_mock, parse_preparser_options_mock, no_config_mock
):
    msg = "expected exit"

    def _raise_sysexit(*args, **kwargs):
        raise SystemExit(msg)

    parse_preparser_options_mock.return_value = argparse.Namespace(
        show_all_opts=True,
        no_plugins=False,
        plug=None,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )
    handle_args_mock.side_effect = _raise_sysexit
    sys_args = [
        "repobee",
        _repobee.cli.preparser.PRE_PARSER_SHOW_ALL_OPTS,
        *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
        "-h",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert msg in str(exc_info.value)
    handle_args_mock.assert_called_once_with(
        [*repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(), "-h"],
        show_all_opts=True,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )
    parse_preparser_options_mock.assert_called_once_with(
        [_repobee.cli.preparser.PRE_PARSER_SHOW_ALL_OPTS]
    )


def test_non_zero_exit_status_on_exception(
    handle_args_mock, parse_preparser_options_mock, no_config_mock
):
    def raise_(*args, **kwargs):
        raise ValueError()

    handle_args_mock.side_effect = raise_

    sys_args = ["repobee", *CLONE_ARGS]

    with pytest.raises(SystemExit) as exc_info:
        main.main(sys_args)

    assert exc_info.value.code == 1


def test_show_config_custom_config():
    config_text = """
[repobee]
user = some-unlikely-user
""".strip()
    with tempfile.NamedTemporaryFile() as tmpfile, patch(
        "_repobee.command.show_config", autospec=True
    ) as show_config_mock:
        config_file = pathlib.Path(tmpfile.name)
        config_file.write_text(config_text)
        sys_args = [
            "repobee",
            "--config-file",
            tmpfile.name,
            *repobee_plug.cli.CoreCommand.config.show.as_name_tuple(),
        ]
        main.main(sys_args)

    show_config_mock.assert_called_once_with(config_file)


workdir_category = plug.cli.category("workdir", ["workdir"])


class TestRun:
    """Tests for the run function."""

    class Workdir(plug.Plugin, plug.cli.Command):
        def command(self, api):
            return plug.Result(
                name="workdir",
                msg="workdir",
                status=plug.Status.SUCCESS,
                data={"cwd": os.getcwd()},
            )

    def test_operates_in_current_workdir_by_default(self):
        results, *_ = list(
            main.run(["workdir"], plugins=[self.Workdir]).values()
        )[0]
        assert results.data["cwd"] == os.getcwd()

    def test_operates_in_specified_workdir(self, tmpdir):
        results, *_ = list(
            main.run(
                ["workdir"], plugins=[self.Workdir], workdir=str(tmpdir)
            ).values()
        )[0]
        assert results.data["cwd"] == str(tmpdir)
