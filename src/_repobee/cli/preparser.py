"""Module for the preparser.

The preparser runs before the primary parser
(see :py:mod:`_repobee.cli.mainparser`). The reason for this somewhat
convoluted setup is that plugins need to be able to add options to the CLI.
As we want to be able to specify plugins on the command line, which may
add options to the command line, this becomes a chicken or egg problem.
The preparser solves this.

.. module:: preparser
    :synopsis: The preparser for RepoBee.

.. moduleauthor:: Simon Larsén
"""

import argparse
import pathlib
from typing import Optional, List, Tuple

import _repobee.cli
import _repobee.constants

PRE_PARSER_PLUG_OPTS = ["-p", "--plug"]
PRE_PARSER_CONFIG_OPTS = ["-c", "--config-file"]
PRE_PARSER_OPTS = PRE_PARSER_PLUG_OPTS + PRE_PARSER_CONFIG_OPTS

PRE_PARSER_NO_PLUGS = "--no-plugins"
# this list should include all pre-parser flags
PRE_PARSER_FLAGS = [PRE_PARSER_NO_PLUGS]


def parse_args(
    sys_args: List[str], default_config_file: pathlib.Path
) -> argparse.Namespace:
    """Parse all arguments that can somehow alter the end-user CLI, such
    as plugins.

    Args:
        sys_args: Command line arguments.
        default_config_file: The default config file to use if none is
            specified.
    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="repobee", description="plugin pre-parser for _repobee."
    )

    add_arguments(parser, default_config_file)
    args = parser.parse_args(sys_args)

    return args


def add_arguments(
    parser: argparse.ArgumentParser,
    default_config_file: Optional[pathlib.Path],
) -> None:
    """Add argument flags that the preparser handles to the given parser.

    Args:
        parser: Parser to add the argument flags to
        default_config_file: The default config file to use
    """
    parser.add_argument(
        *PRE_PARSER_CONFIG_OPTS,
        help="Specify path to the config file to use.",
        type=pathlib.Path,
        default=default_config_file,
    )

    mutex_grp = parser.add_mutually_exclusive_group()
    mutex_grp.add_argument(
        *PRE_PARSER_PLUG_OPTS,
        help="Specify the name of a plugin to use.",
        type=str,
        action="append",
        default=None,
    )
    mutex_grp.add_argument(
        PRE_PARSER_NO_PLUGS, help="Disable plugins.", action="store_true"
    )


def clean_arguments(args: argparse.Namespace) -> None:
    """Cleans the namespace of arguments that were already handled by the
    preprocessor.

    Args:
        args: namespace to clean
    """
    delattr(args, "plug")
    delattr(args, "config_file")
    delattr(args, "no_plugins")


def separate_args(args: List[str]) -> Tuple[List[str], List[str]]:
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
