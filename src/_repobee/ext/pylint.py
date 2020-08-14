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
import pathlib
from typing import Tuple, Union, Iterable


import repobee_plug as plug


PLUGIN_DESCRIPTION = "Runs pylint on student repos after cloning"
SECTION = "pylint"


@plug.repobee_hook
def post_clone(repo: plug.StudentRepo, api: plug.PlatformAPI):
    """Run pylint on all Python files in a repo.

    Args:
        path: Path to the repo.
        api: A platform API class instance.
    Returns:
        a plug.Result specifying the outcome.
    """
    path = repo.path
    python_files = list(path.rglob("*.py"))

    if not python_files:
        msg = "no .py files found"
        return plug.Result(SECTION, plug.Status.WARNING, msg)

    status, msg = _pylint(python_files)
    return plug.Result(name=SECTION, status=status, msg=msg)


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
        plug.echo("Running pylint on {!s}".format(py_file))
        command = "pylint {!s}".format(py_file).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        outfile = pathlib.Path(
            "{}/{}.lint".format(py_file.parent, py_file.name)
        )
        outfile.touch()
        outfile.write_bytes(proc.stdout)
        linted_files.append(str(py_file))

    msg = "linted files: {}".format(", ".join(linted_files))
    return plug.Result(name=SECTION, status=plug.Status.SUCCESS, msg=msg)
