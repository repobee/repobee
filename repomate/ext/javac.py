import subprocess
import sys
import os

import daiquiri

from repomate import tuples
from repomate import util
from repomate import plugin
from repomate.hookspec import hookimpl

LOGGER = daiquiri.getLogger(name=__file__)


@plugin.Plugin
class JavacCloneHook:
    def __init__(self):
        self._ignore = []

    @hookimpl
    def act_on_cloned_repo(self, path):
        """Run javac on all Java files. Requires globbing."""
        java_files = [
            str(file) for file in util.find_files_by_extension(path, '.java')
            if file.name not in self._ignore
        ]
        if not java_files:
            msg = "no .java files found"
            status = plugin.WARNING
            return tuples.HookResult('javac', status, msg)

        command = 'javac {}'.format(' '.join(java_files)).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            status = plugin.ERROR
            msg = proc.stderr.decode(sys.getdefaultencoding())
        else:
            msg = "all files compiled successfully"
            status = plugin.SUCCESS
        return tuples.HookResult('javac', status, msg)

    @hookimpl
    def clone_parser_hook(self, clone_parser):
        """Add ignore files option."""
        clone_parser.add_argument(
            '-i',
            '--ignore',
            help="File names to ignore.",
            nargs='+',
            default=[])

    @hookimpl
    def parse_args(self, args):
        """Get the option stored in -i."""
        if args.ignore:
            self._ignore = args.ignore

    @hookimpl
    def config_hook(self, config_parser):
        """Check for configured ignore files."""
        self._ignore = [
            file.strip()
            for file in config_parser.get('JAVAC', 'ignore', fallback='').split(",")
            if file.strip()
        ]
