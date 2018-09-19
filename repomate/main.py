"""Main entrypoint for the repomate CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repomate CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
import itertools
import daiquiri
import traceback
from typing import List

from repomate import cli
from repomate import plugin

LOGGER = daiquiri.getLogger(__file__)


def _separate_args(args: List[str]) -> (List[str], List[str]):
    """Separate args into plugin args and repomate args."""
    plugin_args = []
    if args and (args[0].startswith('-p') or 'plug' in args[0]):
        cur = 0
        while cur < len(args) and args[cur].startswith('-'):
            if args[cur].startswith('-p'):
                plugin_args += args[cur:cur + 2]
                cur += 2
            elif args[cur] == '--no-plugins':
                plugin_args.append(args[cur])
                cur += 1
            else:
                break
    return plugin_args, args[len(plugin_args):]


def main(sys_args: List[str]):
    """Start the repomate CLI."""
    args = sys_args[1:]  # drop the name of the program
    traceback = False
    try:
        plugin_args, app_args = _separate_args(args)

        if plugin_args:
            parsed_plugin_args = cli.parse_plugins(plugin_args)
            if parsed_plugin_args.no_plugins:
                LOGGER.info("plugins disabled")
            else:
                plugin.initialize_plugins(parsed_plugin_args.plug)
        else:
            plugin.initialize_plugins()
        parsed_args, api = cli.parse_args(app_args)
        traceback = parsed_args.traceback
        cli.dispatch_command(parsed_args, api)
    except Exception as exc:
        if traceback:
            LOGGER.exception("critical exception")
        else:
            LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main(sys.argv)
