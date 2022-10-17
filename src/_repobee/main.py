"""Main entrypoint for the repobee CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repobee CLI application.

.. moduleauthor:: Simon Larsén
"""

import argparse
import contextlib
import dataclasses
import enum
import io
import logging
import os
import pathlib
import sys
from typing import List, Optional, Union, Mapping, Any, NoReturn
from types import ModuleType

import repobee_plug as plug

import _repobee.cli.dispatch
import _repobee.cli.parsing
import _repobee.cli.preparser
import _repobee.cli.mainparser
import _repobee.constants
import _repobee.config
from _repobee import plugin
from _repobee import exception
from _repobee.cli.preparser import separate_args
from _repobee import distinfo
from _repobee import disthelpers


_PRE_INIT_ERROR_MESSAGE = """exception was raised before pre-initialization was
complete. This is usually due to incorrect settings.
Try running the `verify-settings` command and see if
the problem can be resolved. If all fails, please open
an issue at https://github.com/repobee/repobee/issues/new
and supply the stack trace below.""".replace(
    "\n", " "
)


def run(
    cmd: List[str],
    config_file: Union[str, pathlib.Path] = "",
    plugins: Optional[List[Union[ModuleType, plug.Plugin]]] = None,
    workdir: Union[str, pathlib.Path] = ".",
) -> Mapping[str, List[plug.Result]]:
    """Run RepoBee with the provided options. This function is mostly intended
    to be used for testing plugins.

    .. important::

        This function will always unregister all plugins after execution,
        including anly plugins that may have been registered prior to running
        this function.

    Running this function is almost equivalent to running RepoBee from the CLI,
    with the following exceptions:

    1. Preparser options must be passed as arguments to this function (i.e.
       cannot be given as part of ``cmd``).
    2. There is no error handling at the top level, so exceptions are raised
       instead of just logged.

    As an example, the following CLI call:

    .. code-block:: bash

        $ repobee --plug ext.py --config-file config.ini config show

    Can be executed as follows:

    .. code-block:: python

        import ext
        from repobee import run

        run(["config", "show"], config_file="config.ini", plugins=[ext])

    Args:
        cmd: The command to run.
        config_file: Path to the configuration file.
        plugins: A list of plugin modules and/or plugin classes.
        workdir: The working directory to run RepoBee in.
    Returns:
        A mapping (plugin_name -> plugin_results).
    """
    conf = _to_config(pathlib.Path(config_file))
    requested_workdir = pathlib.Path(str(workdir)).resolve(strict=True)

    with _in_workdir(requested_workdir), _unregister_plugins_on_exit():
        _initialize_logging_and_plugins_for_run(plugins or [])
        parsed_args, api = _parse_args(cmd, conf)

        output_verbosity = _get_output_verbosity(parsed_args)
        with _set_output_verbosity(output_verbosity):
            return _repobee.cli.dispatch.dispatch_command(
                parsed_args, api, conf
            )


def _wrap_in_plugin_module(maybe_plugin: Any) -> ModuleType:
    if isinstance(maybe_plugin, type) and issubclass(
        maybe_plugin, plug.Plugin
    ):
        mod = ModuleType(maybe_plugin.__name__.lower())
        mod.__package__ = f"__{maybe_plugin.__name__}"
        setattr(mod, maybe_plugin.__name__, maybe_plugin)
        return mod
    elif isinstance(maybe_plugin, ModuleType):
        return maybe_plugin
    else:
        raise TypeError(f"not plugin or module: {maybe_plugin}")


def _initialize_logging_and_plugins_for_run(plugins: List[Any]):
    wrapped_plugins = list(map(_wrap_in_plugin_module, plugins or []))
    _repobee.cli.parsing.setup_logging()
    _initialize_mandatory_plugins()
    plugin.register_plugins(wrapped_plugins)


@contextlib.contextmanager
def _unregister_plugins_on_exit(unregister: bool = True):
    try:
        yield
    finally:
        if unregister:
            plugin.unregister_all_plugins()


def main(
    sys_args: List[str],
    unload_plugins: bool = True,
    workdir: pathlib.Path = pathlib.Path(".").resolve(),
):
    """Start the repobee CLI.

    Args:
        sys_args: Arguments from the command line.
        unload_plugins: If True, plugins are automatically unloaded just before
            the function returns.
        workdir: The working directory to operate in.
    """
    with _main_error_handler(), _in_workdir(
        workdir
    ), _unregister_plugins_on_exit(unregister=unload_plugins):
        _run_cli(sys_args)


@contextlib.contextmanager
def _main_error_handler():
    try:
        yield
    except plug.PlugError:
        plug.log.error("A plugin exited with an error")
        sys.exit(1)
    except Exception:
        plug.log.error(
            "RepoBee exited unexpectedly. "
            "Please visit the FAQ to try to resolve the problem: "
            "https://repobee.readthedocs.io/en/stable/faq.html"
        )
        sys.exit(1)


def _run_cli(sys_args: List[str]):
    _repobee.cli.parsing.setup_logging()
    args = sys_args[1:]  # drop the name of the program

    with _pre_init_error_handler():
        app_init = _run_preparser_and_init_application(args)

    output_verbosity = _get_output_verbosity(app_init.parsed_args)
    show_traceback = app_init.parsed_args.traceback
    with _set_output_verbosity(output_verbosity), _core_error_handler(
        show_traceback
    ):
        _repobee.cli.dispatch.dispatch_command(
            app_init.parsed_args, app_init.platform_api, app_init.config
        )


@dataclasses.dataclass
class _ApplicationInitialization:
    parsed_args: argparse.Namespace
    # FIXME platform_api should be optional, but typing error in dispatch_command prevents this
    platform_api: plug.PlatformAPI
    config: plug.Config


def _run_preparser_and_init_application(
    args: List[str],
) -> _ApplicationInitialization:
    preparser_args, app_args = separate_args(args)
    parsed_preparser_args = _repobee.cli.preparser.parse_args(
        preparser_args,
        default_config_file=_resolve_config_file(pathlib.Path(".").resolve()),
    )

    # IMPORTANT: the mandatory plugins must be loaded before user-defined
    # plugins to ensure that the user-defined plugins override the defaults
    # in firstresult hooks
    _initialize_mandatory_plugins()
    if not parsed_preparser_args.no_plugins:
        _initialize_non_default_plugins(parsed_preparser_args.plug or [])

    conf = _to_config(parsed_preparser_args.config_file)
    parsed_args, api = _parse_args(app_args, conf)
    return _ApplicationInitialization(parsed_args, api, conf)


@contextlib.contextmanager
def _pre_init_error_handler():
    try:
        yield
    except (
        exception.ParseError,
        exception.PluginLoadError,
        exception.FileError,
    ) as exc:
        plug.echo(_PRE_INIT_ERROR_MESSAGE)
        plug.log.error(f"{exc.__class__.__name__}: {exc}")
        raise
    except Exception as exc:
        plug.echo(_PRE_INIT_ERROR_MESSAGE)
        _handle_unexpected_exception(exc, traceback=True)


@contextlib.contextmanager
def _core_error_handler(traceback: bool):
    try:
        yield
    except Exception as exc:
        _handle_unexpected_exception(exc, traceback=True)


def _handle_unexpected_exception(exc: Exception, traceback: bool) -> NoReturn:
    plug.log.error(f"{exc.__class__.__name__}: {exc}")
    if traceback:
        plug.log.exception("Critical exception")
    raise exc


def _to_config(config_file: pathlib.Path) -> plug.Config:
    if config_file.is_file():
        _repobee.config.check_config_integrity(config_file)
    return plug.Config(config_file)


def _resolve_config_file(path: pathlib.Path) -> pathlib.Path:
    local_config_path = path / _repobee.constants.LOCAL_CONFIG_NAME

    if local_config_path.is_file():
        return local_config_path
    elif path.parent == path:  # file system root
        return _repobee.constants.DEFAULT_CONFIG_FILE
    else:
        return _resolve_config_file(path.parent)


def _initialize_mandatory_plugins():
    plug.log.debug("Initializing default plugins")
    plugin.initialize_default_plugins()

    if distinfo.DIST_INSTALL:
        plug.log.debug("Initializing dist plugins")
        plugin.initialize_dist_plugins()


def _initialize_non_default_plugins(plugin_names: List[str]) -> None:
    if distinfo.DIST_INSTALL:
        plug.log.debug("Initializing active plugins")
        plugin.initialize_plugins(
            disthelpers.get_active_plugins(), allow_filepath=True
        )

    plug.log.debug("Initializing preparser-specified plugins")
    plugin.initialize_plugins(plugin_names, allow_filepath=True)


def _parse_args(args: List[str], config: plug.Config):
    _repobee.config.execute_config_hooks(config)
    parsed_args, api = _repobee.cli.parsing.handle_args(args, config)
    plug.manager.hook.handle_processed_args(args=parsed_args)
    return parsed_args, api


class _OutputVerbosity(enum.IntEnum):
    SILENCE_ERRORS = -3
    SILENCE_WARNINGS = -2
    SILENCE_STDOUT = -1
    STANDARD = 0
    INFO_LOGGING = 1
    DEBUG_LOGGING = 2


@contextlib.contextmanager
def _set_output_verbosity(verbosity: _OutputVerbosity):
    """Set the output verbosity, expecting `quietness` to be a non-negative
    integer.
    """
    if verbosity == _OutputVerbosity.STANDARD:
        yield
        return
    elif verbosity > _OutputVerbosity.STANDARD:
        terminal_level = (
            logging.INFO
            if verbosity == _OutputVerbosity.INFO_LOGGING
            else logging.DEBUG
        )
        _repobee.cli.parsing.setup_logging(terminal_level=terminal_level)
        yield
    else:  # verbosity <= SILENCE_STDOUT
        # silence stdout by redirecting to internal buffer
        with contextlib.redirect_stdout(io.StringIO()):
            if verbosity == _OutputVerbosity.SILENCE_WARNINGS:
                _repobee.cli.parsing.setup_logging(
                    terminal_level=logging.ERROR
                )
            elif verbosity == _OutputVerbosity.SILENCE_ERRORS:
                _repobee.cli.parsing.setup_logging(
                    terminal_level=logging.CRITICAL
                )

            yield


def _get_output_verbosity(parsed_args: argparse.Namespace) -> _OutputVerbosity:
    return _OutputVerbosity(
        -getattr(parsed_args, "quiet", 0) or getattr(parsed_args, "verbose", 0)
    )


@contextlib.contextmanager
def _in_workdir(workdir: pathlib.Path):
    cur_workdir = pathlib.Path(".").resolve()
    try:
        os.chdir(workdir)
        yield
    finally:
        os.chdir(cur_workdir)


if __name__ == "__main__":
    main(sys.argv)
