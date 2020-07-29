"""Utility functions for reading and writing to files."""
import pathlib
import sys
import os
from typing import List

from repobee_plug import _apimeta
from repobee_plug import _exceptions


def parse_students_file(path: pathlib.Path) -> List[_apimeta.Team]:
    """Parse the students file.

    Args:
        path: Path to the students fil.
    Returns:
        A list of teams.
    Raises:
        :py:class:`_exceptions.FileError`
    """
    if not path.is_file():
        raise _exceptions.FileError("'{!s}' is not a file".format(path))
    if not path.stat().st_size:
        raise _exceptions.FileError("'{!s}' is empty".format(path))
    return [
        _apimeta.Team(members=[s for s in group.strip().split()])
        for group in path.read_text(encoding=sys.getdefaultencoding()).split(
            os.linesep
        )
        if group  # skip blank lines
    ]
