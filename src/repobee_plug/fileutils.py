"""Utility functions for reading and writing to files."""
import pathlib
import sys
import os
import hashlib
from typing import List, Union

from repobee_plug import exceptions
from repobee_plug.name import generate_repo_name

from repobee_plug.localreps import StudentTeam

__all__ = ["parse_students_file", "hash_path", "generate_repo_path"]


def parse_students_file(path: pathlib.Path) -> List[StudentTeam]:
    """Parse the students file.

    Args:
        path: Path to the students fil.
    Returns:
        A list of teams.
    Raises:
        :py:class:`exceptions.FileError`
    """
    if not path.is_file():
        raise exceptions.FileError("'{!s}' is not a file".format(path))
    if not path.stat().st_size:
        raise exceptions.FileError("'{!s}' is empty".format(path))
    return [
        StudentTeam(members=[s for s in group.strip().split()])
        for group in path.read_text(encoding=sys.getdefaultencoding()).split(
            os.linesep
        )
        if group  # skip blank lines
    ]


def hash_path(path: Union[str, pathlib.Path]) -> str:
    """Hash the path with SHA1.

    .. important::

        This is not a security function, it's just to avoid name collisions in.

    Args:
        path: A path to hash.
    Returns:
        The hexdigest of the SHA1 hash of the path.
    """
    enc = sys.getdefaultencoding()
    return hashlib.sha1(str(path).encode(enc)).hexdigest()  # nosec


def generate_repo_path(
    root: Union[str, pathlib.Path], team_name: str, template_repo_name: str
) -> pathlib.Path:
    """Generate a relative path to the student repo.

    Args:
        team_name: Name of the student team.
        template_repo_name: Name of the template repo.
    Returns:
        A relative path to the student repo.
    """
    return (
        pathlib.Path(root)
        / team_name
        / generate_repo_name(team_name, template_repo_name)
    )
