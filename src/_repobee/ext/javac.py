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
import pathlib
from typing import Union, Iterable, Tuple

from _repobee import util

import repobee_plug as plug

PLUGIN_NAME = "javac"
PLUGIN_DESCRIPTION = "Runs javac on student repos after cloning"


class JavacCloneHook(plug.Plugin, plug.cli.CommandExtension):
    """Containe for the plugin hooks allowing for persistence between
    adding/parsing arguments and acting on the repo.
    """

    __settings__ = plug.cli.command_extension_settings(
        actions=[plug.cli.CoreCommand.repos.clone]
    )

    javac_ignore = plug.cli.option(
        help="Filenames to ignore.",
        configurable=True,
        argparse_kwargs={"nargs": "+"},
    )

    def post_clone(
        self, repo: plug.StudentRepo, api: plug.PlatformAPI
    ) -> plug.Result:
        """Run ``javac`` on all .java files in the repo.

        Args:
            repo: A student repo.
            api: A platform API class instance.
        Returns:
            a Result specifying the outcome.
        """
        ignore = list(self.javac_ignore) or []
        java_files = [
            str(file)
            for file in util.find_files_by_extension(repo.path, ".java")
            if file.name not in ignore
        ]

        if not java_files:
            msg = "no .java files found"
            status = plug.Status.WARNING
            return plug.Result(PLUGIN_NAME, status, msg)

        status, msg = self._javac(java_files)
        return plug.Result(PLUGIN_NAME, status, msg)

    def _javac(
        self, java_files: Iterable[Union[str, pathlib.Path]]
    ) -> Tuple[str, str]:
        """Run ``javac`` on all of the specified files, assuming that they are
        all ``.java`` files.

        Args:
            java_files: paths to ``.java`` files.
        Returns:
            (status, msg), where status is e.g. is a
            :py:class:`repobee_plug.Status` code and the message describes the
            outcome in plain text.
        """
        command = ["javac", *[str(path) for path in java_files]]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if proc.returncode != 0:
            status = plug.Status.ERROR
            msg = proc.stderr.decode(sys.getdefaultencoding())
        else:
            msg = "all files compiled successfully"
            status = plug.Status.SUCCESS

        return status, msg
