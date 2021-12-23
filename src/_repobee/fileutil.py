"""Utility functions for dealing with files and directories.

.. module:: fileutil
    :synopsis: Utility functions for dealing with files and directories.
"""
import os
import enum
import pathlib
import shutil
import sys
import tempfile
from typing import Iterable, Generator, Union

import repobee_plug as plug

__all__ = ["DirectoryLayout"]


def _flat_repo_path(
    base: pathlib.Path, repo: plug.StudentRepo
) -> pathlib.Path:
    return base / repo.name


def _by_team_repo_path(
    base: pathlib.Path, repo: plug.StudentRepo
) -> pathlib.Path:
    return base / repo.team.name / repo.name


class DirectoryLayout(enum.Enum):
    """Layouts for arranging repositories on disk."""

    FLAT = "flat"
    BY_TEAM = "by-team"

    def __init__(self, label: str):
        self.label = label
        self.get_repo_path = {
            "flat": _flat_repo_path,
            "by-team": _by_team_repo_path,
        }[label]

    def __str__(self):
        return str(self.label)


def find_files_by_extension(
    root: Union[str, pathlib.Path], *extensions: str
) -> Generator[pathlib.Path, None, None]:
    """Find all files with the given file extensions, starting from root.

    Args:
        root: The directory to start searching.
        extensions: One or more file extensions to look for.
    Returns:
        a generator that yields a Path objects to the files.
    """
    if not extensions:
        raise ValueError("must provide at least one extension")
    for cwd, _, files in os.walk(root):
        for file in files:
            if _ends_with_ext(file, extensions):
                yield pathlib.Path(cwd) / file


def _ends_with_ext(
    path: Union[str, pathlib.Path], extensions: Iterable[str]
) -> bool:
    _, ext = os.path.splitext(str(path))
    return ext in extensions


def atomic_write(content: str, dst: pathlib.Path) -> None:
    """Write the given contents to the destination "atomically". Achieved by
    writin in a temporary directory and then moving the file to the
    destination.

    Args:
        content: The content to write to the new file.
        dst: Path to the file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(
            delete=False, dir=tmpdir, mode="w"
        ) as file:
            file.write(content)

        shutil.move(file.name, str(dst))


def read_issue_from_file(issue_path: str) -> plug.Issue:
    """Attempt to read an issue from a textfile. The first line of the file
    is interpreted as the issue's title.

    Args:
        issue_path: Local path to textfile with an issue.
    """
    if not os.path.isfile(issue_path):
        raise ValueError(f"{issue_path} is not a file")
    with open(issue_path, "r", encoding=sys.getdefaultencoding()) as file:
        return plug.Issue(file.readline().strip(), file.read())
