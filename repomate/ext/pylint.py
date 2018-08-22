"""Plugin that runs javac on all files in a repo.

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
import os
import pathlib
from typing import Tuple, Union, Iterable

import daiquiri

from repomate import plugin
from repomate import tuples
from repomate import util
from repomate.hookspec import hookimpl

LOGGER = daiquiri.getLogger(name=__file__)


@hookimpl
def act_on_cloned_repo(path: Union[str, pathlib.Path]):
    """Run pylint on all Python files in a repo.
    
    Args:
        path: Path to the repo.
    Returns:
        a tuples.HookResult specifying the outcome.
    """
    python_files = list(util.find_files_by_extension(path, '.py'))

    if not python_files:
        msg = "no .py files found"
        status = "warning"
        return tuples.HookResult('pylint', status, msg)

    status, msg = _pylint(python_files)
    return tuples.HookResult(hook="pylint", status="success", msg=msg)


def _pylint(
        python_files: Iterable[Union[str, pathlib.Path]]) -> Tuple[str, str]:
    """Run ``pylint`` on all of the specified files.

    Args:
        python_files: paths to ``.py`` files.
    Returns:
        (status, msg), where status is e.g. :py:const:`plugin.ERROR` and
        the message describes the outcome in plain text.
    """
    linted_files = []
    for cwd, py_file in python_files:
        LOGGER.info("running pylint on {}".format(py_file))
        infile = os.path.join(cwd, py_file)
        outfile = os.path.join(cwd, "{}.lint".format(py_file))
        command = 'pylint {}'.format(infile).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(outfile, 'w', encoding='utf8') as f:
            f.write(proc.stdout.decode('utf8'))
        linted_files.append(py_file)

    msg = "linted files: {}".format(", ".join(linted_files))
    return plugin.SUCCESS, msg
