"""Some general utility functions.

.. module:: util
    :synopsis: Miscellaneous utility functions that don't really belong
        anywhere else.

.. moduleauthor:: Simon Larsén
"""
import os
import sys
import pathlib
from typing import Iterable, Generator, Union, Set

from repobee_plug import apimeta


def read_issue(issue_path: str) -> apimeta.Issue:
    """Attempt to read an issue from a textfile. The first line of the file
    is interpreted as the issue's title.

    Args:
        issue_path: Local path to textfile with an issue.
    """
    if not os.path.isfile(issue_path):
        raise ValueError("{} is not a file".format(issue_path))
    with open(issue_path, "r", encoding=sys.getdefaultencoding()) as file:
        return apimeta.Issue(file.readline().strip(), file.read())


def generate_repo_name(team_name: str, master_repo_name: str) -> str:
    """Construct a repo name for a team.

    Args:
        team_name: Name of the associated team.
        master_repo_name: Name of the template repository.
    """
    return "{}-{}".format(team_name, master_repo_name)


def conflicting_files(filenames: Iterable[str], cwd: str = ".") -> Set[str]:
    """Return a list of files (any kind of file, including directories, pipes
    etc) in cwd that conflict with any of the given repo names.

    Args:
        repo_names: A list of filenames.
        cwd: Directory to operate in.
    Returns:
        A set of conflicting filenames.
    """
    existing_filenames = set(os.listdir(cwd))
    return set(filenames).intersection(existing_filenames)


def generate_repo_names(
    team_names: Iterable[str], master_repo_names: Iterable[str]
) -> Iterable[str]:
    """Construct all combinations of generate_repo_name(team_name,
    master_repo_name) for the provided team names and master repo names.

    Args:
        team_names: One or more names of teams.
        master_repo_names: One or more names of master repositories.

    Returns:
        a list of repo names for all combinations of team and master repo.
    """
    master_repo_names = list(
        master_repo_names
    )  # needs to be traversed multiple times
    return [
        generate_repo_name(team_name, master_name)
        for master_name in master_repo_names
        for team_name in team_names
    ]


def generate_review_team_name(student: str, master_repo_name: str) -> str:
    """Generate a review team name.

    Args:
        student: A student username.
        master_repo_name: Name of a master repository.

    Returns:
        a review team name for the student repo associated with this master
        repo and student.
    """
    return generate_repo_name(student, master_repo_name) + "-review"


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
