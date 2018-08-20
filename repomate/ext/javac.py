import subprocess
import sys
import os

import daiquiri

from repomate import tuples
from repomate.hookspec import hookimpl
from repomate.plugin import Plugin

LOGGER = daiquiri.getLogger(name=__file__)


def _java_files(root, ignore=[]):
    for cwd, dirs, files in os.walk(root):
        for file in files:
            if file.endswith('.java') and file not in ignore:
                yield os.path.join(cwd, file)


@Plugin
class JavacCloneHook:
    def __init__(self):
        self._ignore = []

    @hookimpl
    def act_on_cloned_repo(self, path):
        """Run javac on all Java files. Requires globbing."""
        java_files = list(_java_files(path, self._ignore))
        if not java_files:
            LOGGER.error("no java files found in {}".format(path))
            msg = "no .java files found"
            status = "warning"
            return tuples.HookResult('javac', status, msg)

        LOGGER.info("found java files: {}".format(java_files))

        command = 'javac {}'.format(' '.join(java_files)).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            status = "error"
            msg = proc.stderr.decode(sys.getdefaultencoding())
            #LOGGER.warning("Compilation error")
            #LOGGER.warning(proc.stderr.decode("utf-8"))
        else:
            msg = "all files compiled successfully"
            status = "success"
            #LOGGER.info("All files compiled successfully")
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
    def config_hook(self, config):
        """Check for configured ignore files."""
        if "JAVAC" in config and "ignore" in config["JAVAC"]:
            self._ignore = [
                file.strip() for file in config["JAVAC"]["ignore"].split(",")
            ]
