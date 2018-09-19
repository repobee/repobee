"""Main entrypoint for the repomate CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repomate CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
import itertools
import daiquiri
from typing import List

from repomate import cli
from repomate import plugin

LOGGER = daiquiri.getLogger(__file__)


def main(sys_args: List[str]):
    """Start the repomate CLI."""
    args = sys_args[1:]  # drop the name of the program
    try:
        if args and (args[0].startswith('-p') or 'plugin' in args[0]):
            plugin_args = list(
                itertools.takewhile(lambda arg: arg not in cli.PARSER_NAMES,
                                    args))
            parsed_plugin_args = cli.parse_plugins(plugin_args)
            if parsed_plugin_args.no_plugins:
                LOGGER.info("plugins disabled")
            else:
                plugin.initialize_plugins(parsed_plugin_args.plug)
            args = args[len(plugin_args):]
        else:
            plugin.initialize_plugins()
        parsed_args, api = cli.parse_args(args)
        cli.dispatch_command(parsed_args, api)
    except Exception as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main(sys.argv)
