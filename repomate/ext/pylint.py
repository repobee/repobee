"""Plugin that runs pylint on all files in a repo.

.. important::

    Requires ``pylint`` to be installed and accessible by the script!

This plugin is mostly for demonstrational purposes, showing how to make the
most barebones of plugins using only a single function. It finds all ``.py``
files in a repo, and runs pylint on them, storing the results in files named
``<filename>.lint`` for any ``.py`` file named ``filename``.

.. module:: pylint
    :synopsis: Plugin that runs pylint on all .py files in a repo.

.. moduleauthor:: Simon Larsén
"""

import subprocess
import sys
import pathlib
from typing import Tuple, Union, Iterable

import daiquiri

from repomate import plugin
from repomate import tuples
from repomate import util

from repomate_plug import repomate_hook, HookResult, Status

LOGGER = daiquiri.getLogger(name=__file__)

SECTION = 'pylint'


@repomate_hook
def act_on_cloned_repo(path: Union[str, pathlib.Path]):
    """Run pylint on all Python files in a repo.
    
    Args:
        path: Path to the repo.
    Returns:
        a plug.HookResult specifying the outcome.
    """
    path = pathlib.Path(path)
    python_files = list(path.rglob('*.py'))

    if not python_files:
        msg = "no .py files found"
        return HookResult(SECTION, Status.WARNING, msg)

    status, msg = _pylint(python_files)
    return HookResult(hook=SECTION, status=Status.SUCCESS, msg=msg)


def _pylint(python_files: Iterable[Union[pathlib.Path]]) -> Tuple[str, str]:
    """Run ``pylint`` on all of the specified files.

    Args:
        python_files: paths to ``.py`` files.
    Returns:
        (status, msg), where status is e.g. :py:const:`plugin.ERROR` and
        the message describes the outcome in plain text.
    """
    linted_files = []
    for py_file in python_files:
        LOGGER.info("running pylint on {!s}".format(py_file))
        command = 'pylint {!s}'.format(py_file).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        outfile = pathlib.Path("{}/{}.lint".format(py_file.parent,
                                                   py_file.name))
        outfile.touch()
        outfile.write_bytes(proc.stdout)
        linted_files.append(str(py_file))

    msg = "linted files: {}".format(", ".join(linted_files))
    return HookResult(hook=SECTION, status=Status.SUCCESS, msg=msg)
