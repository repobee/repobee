"""Plugin that runs javac on all files in a repo.

.. important::

    Requires ``javac`` to be installed and accessible by the script!

This plugin is mostly for demonstrational purposes, showing off some of the
more advanced features of the plugin system. It, very unintelligently, finds
all of the ``.java`` files in a repository and tries to compile them all at the
same time. Duplicate files etc. will cause this to fail.

The point of this plugin is however mostly to demonstrate how to use the hooks,
and specifically the more advanced use of the ``clone_parser_hook`` and
``parse_args`` hooks.

.. module:: javac
    :synopsis: Plugin that tries to compile all .java files in a repo.

.. moduleauthor:: Simon Larsén
"""
import subprocess
import sys
import os
import argparse
import configparser
import pathlib
from typing import Union, Iterable, Tuple

import daiquiri

from repomate import tuples
from repomate import util

from repomate_plug import Plugin, HookResult, Status

LOGGER = daiquiri.getLogger(name=__file__)

SECTION = 'javac'


class JavacCloneHook(Plugin):
    """Containe for the plugin hooks allowing for persistence between
    adding/parsing arguments and acting on the repo.
    """

    def __init__(self):
        self._ignore = []

    def act_on_cloned_repo(self, path: Union[str, pathlib.Path]) -> HookResult:
        """Run ``javac`` on all .java files in the repo.
        
        Args:
            path: Path to the repo.
        Returns:
            a HookResult specifying the outcome.
        """
        java_files = [
            str(file) for file in util.find_files_by_extension(path, '.java')
            if file.name not in self._ignore
        ]

        if not java_files:
            msg = "no .java files found"
            status = Status.WARNING
            return HookResult('javac', status, msg)

        status, msg = self._javac(java_files)
        return HookResult('javac', status, msg)

    def _javac(self, java_files: Iterable[Union[str, pathlib.Path]]
               ) -> Tuple[str, str]:
        """Run ``javac`` on all of the specified files, assuming that they are
        all ``.java`` files.

        Args:
            java_files: paths to ``.java`` files.
        Returns:
            (status, msg), where status is e.g. is a
            :py:class:`repomate_plug.Status` code and the message describes the
            outcome in plain text.
        """
        command = ["javac", *[str(path) for path in java_files]]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            status = Status.ERROR
            msg = proc.stderr.decode(sys.getdefaultencoding())
        else:
            msg = "all files compiled successfully"
            status = Status.SUCCESS

        return status, msg

    def clone_parser_hook(self, clone_parser: argparse.ArgumentParser) -> None:
        """Add ignore files option to the clone parser. All filenames specified
        will be ignored when running the :py:func:`act_on_cloned_repo` function.

        Args:
            clone_parser: The ``clone`` subparser.
        """
        clone_parser.add_argument(
            '-i', '--ignore', help="File names to ignore.", nargs='+')

    def parse_args(self, args: argparse.Namespace) -> None:
        """Get the option stored in the ``--ignore`` option added by
        :py:func:`clone_parser_hook`.

        Args:
            args: The full namespace returned by
            :py:func:`argparse.ArgumentParser.parse_args`
        """
        if args.ignore:
            self._ignore = args.ignore

    def config_hook(self, config_parser: configparser.ConfigParser) -> None:
        """Check for configured ignore files.
        
        Args:
            config: the config parser after config has been read.
        """
        self._ignore = [
            file.strip() for file in config_parser.get(
                SECTION, 'ignore', fallback='').split(",") if file.strip()
        ]
