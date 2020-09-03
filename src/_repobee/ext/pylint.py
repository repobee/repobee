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
import shlex
import sys
import dataclasses
from typing import List


import repobee_plug as plug


PLUGIN_DESCRIPTION = "Runs pylint on student repos after cloning"
SECTION = "pylint"


@dataclasses.dataclass(frozen=True)
class _PylintResult:
    path: pathlib.Path
    output: str
    errored: bool


@plug.repobee_hook
def post_clone(repo: plug.StudentRepo, api: plug.PlatformAPI) -> plug.Result:
    """Run pylint on all Python files in a repo.

    Args:
        path: Path to the repo.
        api: A platform API class instance.
    Returns:
        a plug.Result specifying the outcome.
    """
    lint_results = _pylint(repo.path)
    if not lint_results:
        msg = "no .py files found"
        return plug.Result(SECTION, plug.Status.WARNING, msg)

    msg = "\n".join(
        [
            f"{res.path} -- {'ERROR' if res.errored else 'OK'}"
            for res in lint_results
        ],
    )
    has_errors = any(map(lambda res: res.errored != 0, lint_results))

    return plug.Result(
        name=SECTION,
        msg=msg,
        status=plug.Status.SUCCESS if not has_errors else plug.Status.ERROR,
        data={
            str(pylint_res.path): pylint_res.output
            for pylint_res in lint_results
        },
    )


def _pylint(basedir: pathlib.Path) -> List[_PylintResult]:
    """Run ``pylint`` on all python files in the specified directory.

    Args:
        basedir: The base directory to search for files in.
    Returns:
        A list of results from running pylint.
    """
    python_files = list(basedir.rglob("*.py"))

    linted_files = []
    for py_file in python_files:
        command = shlex.split(f"pylint {py_file}")

        full_lint = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        error_lint = subprocess.run(
            command + ["--errors-only"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        output = full_lint.stdout.decode(sys.getdefaultencoding())
        errored = error_lint.returncode != 0

        linted_files.append(
            _PylintResult(
                path=py_file.relative_to(basedir),
                output=output,
                errored=errored,
            )
        )

    return linted_files
