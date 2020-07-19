"""Module for the preparser.

The preparser runs before the primary parser
(see :py:mod:`_repobee.cli.mainparser`). The reason for this somewhat
convoluted setup is that:

1. Plugins need to be able to add options to the CLI, which is only
possible if a separate parser runs before the primary parser.
2. Certain options affect how the CLI behaves, such as ``--show-all-opts``.

.. module:: preparser
    :synopsis: The preparser for RepoBee.

.. moduleauthor:: Simon Larsén
"""

import argparse
import pathlib
from typing import List

import _repobee.cli
import _repobee.constants

PRE_PARSER_PLUG_OPTS = ["-p", "--plug"]
PRE_PARSER_CONFIG_OPTS = ["-c", "--config-file"]
PRE_PARSER_OPTS = PRE_PARSER_PLUG_OPTS + PRE_PARSER_CONFIG_OPTS

PRE_PARSER_NO_PLUGS = "--no-plugins"
PRE_PARSER_SHOW_ALL_OPTS = "--show-all-opts"
# this list should include all pre-parser flags
PRE_PARSER_FLAGS = [PRE_PARSER_NO_PLUGS, PRE_PARSER_SHOW_ALL_OPTS]


def parse_args(sys_args: List[str]) -> argparse.Namespace:
    """Parse all arguments that can somehow alter the end-user CLI, such
    as plugins.

    Args:
        sys_args: Command line arguments.
    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="repobee", description="plugin pre-parser for _repobee."
    )

    parser.add_argument(
        *PRE_PARSER_CONFIG_OPTS,
        help="Specify path to the config file to use.",
        type=pathlib.Path,
        default=_repobee.constants.DEFAULT_CONFIG_FILE
    )
    parser.add_argument(
        PRE_PARSER_SHOW_ALL_OPTS,
        help="Unsuppress all options in help menus",
        action="store_true",
    )

    mutex_grp = parser.add_mutually_exclusive_group()
    mutex_grp.add_argument(
        *PRE_PARSER_PLUG_OPTS,
        help="Specify the name of a plugin to use.",
        type=str,
        action="append",
        default=None
    )
    mutex_grp.add_argument(
        PRE_PARSER_NO_PLUGS, help="Disable plugins.", action="store_true"
    )

    args = parser.parse_args(sys_args)

    return args


def separate_args(args: List[str]) -> (List[str], List[str]):
    """Separate args into preparser args and primary parser args.

    Args:
        args: Raw command line arguments.
    Returns:
        A tuple of lists (preparser_args, mainparser_args).
    """
    preparser_args = []
    if args and args[0].startswith("-"):
        cur = 0
        while cur < len(args) and args[cur].startswith("-"):
            if args[cur] in _repobee.cli.preparser.PRE_PARSER_OPTS:
                preparser_args += args[cur : cur + 2]
                cur += 2
            elif args[cur] in _repobee.cli.preparser.PRE_PARSER_FLAGS:
                preparser_args.append(args[cur])
                cur += 1
            else:
                break
    return preparser_args, args[len(preparser_args) :]
