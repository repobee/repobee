"""Main entrypoint for the repobee CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repobee CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
from typing import List

import daiquiri
import repobee_plug as plug

from _repobee import cli
from _repobee import plugin
from _repobee import exception
from _repobee import constants

LOGGER = daiquiri.getLogger(__file__)

_PRE_INIT_ERROR_MESSAGE = """exception was raised before pre-initialization was
complete. This is usually due to incorrect settings.
Try running the `verify-settings` command and see if
the problem can be resolved. If all fails, please open
an issue at https://github.com/repobee/repobee/issues/new
and supply the stack trace below.""".replace(
    "\n", " "
)


def _separate_args(args: List[str]) -> (List[str], List[str]):
    """Separate args into preparser args and repobee args."""
    preparser_args = []
    if args and args[0].startswith("-"):
        cur = 0
        while cur < len(args) and args[cur].startswith("-"):
            if args[cur] in cli.PRE_PARSER_PLUG_OPTS:
                preparser_args += args[cur : cur + 2]
                cur += 2
            elif args[cur] in cli.PRE_PARSER_FLAGS:
                preparser_args.append(args[cur])
                cur += 1
            else:
                break
    return preparser_args, args[len(preparser_args) :]


def main(sys_args: List[str]):
    """Start the repobee CLI."""
    args = sys_args[1:]  # drop the name of the program
    traceback = False
    pre_init = True
    try:
        preparser_args, app_args = _separate_args(args)
        parsed_preparser_args = cli.parse_preparser_options(preparser_args)

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

        ext_commands = plug.manager.hook.create_extension_command()
        parsed_args, api = cli.parse_args(
            app_args,
            show_all_opts=parsed_preparser_args.show_all_opts,
            ext_commands=ext_commands,
        )
        traceback = parsed_args.traceback
        pre_init = False
        cli.dispatch_command(parsed_args, api, ext_commands)
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


if __name__ == "__main__":
    main(sys.argv)
