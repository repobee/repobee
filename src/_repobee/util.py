"""Some general utility functions.

.. module:: util
    :synopsis: Miscellaneous utility functions that don't really belong
        anywhere else.

.. moduleauthor:: Simon Larsén
"""
import os
import sys
import pathlib
import shutil
import tempfile
from typing import Iterable, Generator, Union, Callable, TypeVar

import repobee_plug as plug

T = TypeVar("T")


def read_issue(issue_path: str) -> plug.Issue:
    """Attempt to read an issue from a textfile. The first line of the file
    is interpreted as the issue's title.

    Args:
        issue_path: Local path to textfile with an issue.
    """
    if not os.path.isfile(issue_path):
        raise ValueError("{} is not a file".format(issue_path))
    with open(issue_path, "r", encoding=sys.getdefaultencoding()) as file:
        return plug.Issue(file.readline().strip(), file.read())


def repo_name(repo_url: str) -> str:
    """Extract the name of the repo from its url.

    Args:
        repo_url: A url to a repo.
    """
    repo_name = repo_url.split("/")[-1]
    if repo_name.endswith(".git"):
        return repo_name[:-4]
    return repo_name


def is_git_repo(path: str) -> bool:
    """Check if a directory has a .git subdirectory.

    Args:
        path: Path to a local directory.
    Returns:
        True if there is a .git subdirectory in the given directory.
    """
    return os.path.isdir(path) and ".git" in os.listdir(path)


def _ends_with_ext(
    path: Union[str, pathlib.Path], extensions: Iterable[str]
) -> bool:
    _, ext = os.path.splitext(str(path))
    return ext in extensions


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


def call_if_defined(func: Callable[..., T], *args, **kwargs) -> T:
    """Call the function with the provided args and kwargs if it is defined
    (i.e. not None). This is mostly useful for plugin data structures that have
    optional functions.

    Args:
        func: A function to call.
        args: Positional arguments.
        kwargs: Keyword arguments.
    Returns:
        What ``func`` returns, or ``None`` if ``func`` is ``None``.
    """
    return None if func is None else func(*args, **kwargs)
