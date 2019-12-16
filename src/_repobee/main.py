"""Main entrypoint for the repobee CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repobee CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
from typing import List

import daiquiri
import repobee_plug as plug

import _repobee.cli.dispatch
import _repobee.cli.parsing
import _repobee.cli.preparser
from _repobee import plugin
from _repobee import exception
from _repobee import constants
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


def main(sys_args: List[str]):
    """Start the repobee CLI."""
    _repobee.cli.parsing.setup_logging()
    args = sys_args[1:]  # drop the name of the program
    traceback = False
    pre_init = True
    try:
        preparser_args, app_args = separate_args(args)
        parsed_preparser_args = _repobee.cli.preparser.parse_args(
            preparser_args
        )

        if parsed_preparser_args.no_plugins:
            LOGGER.info("Non-default plugins disabled")
            plugin.initialize_plugins([constants.DEFAULT_PLUGIN])
        else:
            plugin_names = plugin.resolve_plugin_names(
                parsed_preparser_args.plug, constants.DEFAULT_CONFIG_FILE
            )
            # IMPORTANT: the default plugin MUST be loaded last to ensure that
            # any user-defined plugins override the firstresult hooks
            plugin.initialize_plugins(
                plugin_names + [constants.DEFAULT_PLUGIN]
            )

        config.execute_config_hooks()
        ext_commands = plug.manager.hook.create_extension_command()
        parsed_args, api = _repobee.cli.parsing.handle_args(
            app_args,
            show_all_opts=parsed_preparser_args.show_all_opts,
            ext_commands=ext_commands,
        )
        traceback = parsed_args.traceback
        pre_init = False
        _repobee.cli.dispatch.dispatch_command(parsed_args, api, ext_commands)
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


if __name__ == "__main__":
    main(sys.argv)
