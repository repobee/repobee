"""Hook specifications.

.. module:: hookspec
    :synopsis: Hook specifications.

.. moduleauthor:: Simon Larsén
"""
import pathlib
import argparse
import configparser
from typing import Union

import pluggy

hookspec = pluggy.HookspecMarker(__package__)
hookimpl = pluggy.HookimplMarker(__package__)

pm = pluggy.PluginManager(__package__)


class CloneHook:
    """Hook functions related to cloning repos."""

    @hookspec
    def act_on_cloned_repo(self, path: Union[str, pathlib.Path]):
        """Do something with a cloned repo.

        Args:
            path: Path to the repo.
        """

    @hookspec
    def clone_parser_hook(self, clone_parser: argparse.ArgumentParser):
        """Do something with the clone repos subparser before it is used used to
        parse CLI options. The typical task is to add options to it.

        Args:
            clone_parser: The ``clone`` subparser.
        """

    @hookspec
    def parse_args(self, args: argparse.Namespace):
        """Get the raw args from the parser. Only called for the clone parser.
        The typical task is to fetch any values from options added in
        :py:func:`clone_parser_hook`.

        Args:
            args: The full namespace returned by
            :py:func:`argparse.ArgumentParser.parse_args`
        """

    @hookspec
    def config_hook(self, config: configparser.ConfigParser):
        """Hook into the config file parsing.
        
        Args:
            config: the config parser after config has been read.
        """


pm.add_hookspecs(CloneHook)
