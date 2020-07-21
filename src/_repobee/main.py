"""Main entrypoint for the repobee CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repobee CLI application.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import sys
from typing import List, Optional, Union, Mapping
from types import ModuleType

import daiquiri
import repobee_plug as plug

import _repobee.cli.dispatch
import _repobee.cli.parsing
import _repobee.cli.preparser
import _repobee.distinfo
from _repobee import plugin
from _repobee import exception
from _repobee import config
from _repobee.cli.preparser import separate_args

LOGGER = daiquiri.getLogger(__file__)

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
    show_all_opts: bool = False,
    config_file: Union[str, pathlib.Path] = "",
    plugins: Optional[List[Union[ModuleType, plug.Plugin]]] = None,
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
        show_all_opts: Equivalent to the ``--show-all-opts`` flag.
        config_file: Path to the configuration file.
        plugins: A list of plugin modules and/or plugin classes.
    Returns:
        A mapping (plugin_name -> plugin_results).
    """
    config_file = pathlib.Path(config_file)

    def _ensure_is_module(p: Union[ModuleType, plug.Plugin]):
        if issubclass(p, plug.Plugin):
            mod = ModuleType(p.__name__.lower())
            mod.__package__ = f"__{p.__name__}"
            setattr(mod, p.__name__, p)
            return mod
        elif isinstance(p, ModuleType):
            return p
        else:
            raise TypeError(f"not plugin or module: {p}")

    wrapped_plugins = list(map(_ensure_is_module, plugins or []))
    try:
        _repobee.cli.parsing.setup_logging()
        plugin.initialize_default_plugins()
        plugin.register_plugins(wrapped_plugins)
        parsed_args, api, ext_commands = _parse_args(
            cmd, config_file, show_all_opts
        )
        _repobee.cli.dispatch.dispatch_command(
            parsed_args, api, config_file, ext_commands
        )
    finally:
        plugin.unregister_all_plugins()


def main(sys_args: List[str], unload_plugins: bool = True):
    """Start the repobee CLI.

    Args:
        sys_args: Arguments from the command line.
        unload_plugins: If True, plugins are automatically unloaded just before
            the function returns.
    """
    _repobee.cli.parsing.setup_logging()
    args = sys_args[1:]  # drop the name of the program
    traceback = False
    pre_init = True
    try:
        preparser_args, app_args = separate_args(args)
        parsed_preparser_args = _repobee.cli.preparser.parse_args(
            preparser_args
        )
        config_file = parsed_preparser_args.config_file

        # IMPORTANT: the default plugins must be loaded before user-defined
        # plugins to ensure that the user-defined plugins override the defaults
        # in firstresult hooks
        LOGGER.debug("Initializing default plugins")
        plugin.initialize_default_plugins()
        if _repobee.distinfo.DIST_INSTALL:
            LOGGER.debug("Initializing dist plugins")
            plugin.initialize_dist_plugins()

        if not parsed_preparser_args.no_plugins:
            LOGGER.debug("Initializing user plugins")
            plugin_names = (
                parsed_preparser_args.plug
                or config.get_plugin_names(config_file)
            ) or []
            plugin.initialize_plugins(plugin_names, allow_filepath=True)

        parsed_args, api, ext_commands = _parse_args(
            app_args, config_file, parsed_preparser_args.show_all_opts
        )
        traceback = parsed_args.traceback
        pre_init = False
        _repobee.cli.dispatch.dispatch_command(
            parsed_args, api, config_file, ext_commands
        )
    except exception.PluginLoadError as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))
        LOGGER.error(
            "The plugin may not be installed, or it may not exist. If the "
            "plugin is defined in the config file, try running `repobee "
            "--no-plugins config-wizard` to remove any offending plugins."
        )
        sys.exit(1)
    except Exception as exc:
        # FileErrors can occur during pre-init because of reading the config
        # and we don't want tracebacks for those (afaik at this time)
        if traceback or (
            pre_init and not isinstance(exc, exception.FileError)
        ):
            LOGGER.error(str(exc))
            if pre_init:
                LOGGER.info(_PRE_INIT_ERROR_MESSAGE)
            LOGGER.exception("Critical exception")
        else:
            LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))
        sys.exit(1)
    finally:
        if unload_plugins:
            plugin.unregister_all_plugins()


def _parse_args(args, config_file, show_all_opts):
    config.execute_config_hooks(config_file)
    ext_commands = plug.manager.hook.create_extension_command()
    parsed_args, api = _repobee.cli.parsing.handle_args(
        args,
        show_all_opts=show_all_opts,
        ext_commands=ext_commands,
        config_file=config_file,
    )
    return parsed_args, api, ext_commands


if __name__ == "__main__":
    main(sys.argv)
