"""Wrapper functions for git commands that perform local git operations.

.. module:: git
    :synopsis: Wrapper functions for git commands that perform local git
    operations, such as initializing git repository, stashing changes, etc.
"""

import pathlib
import subprocess
from typing import (
    List,
    Mapping,
    Any,
)

import git

import repobee_plug as plug


def set_gitconfig_options(
    repo_path: pathlib.Path, options: Mapping[str, Any]
) -> None:
    """Set gitconfig options in the repository.

    Args:
        repo_path: Path to a repository.
        options: A mapping (option_name -> option_value)
    """
    repo = git.Repo(repo_path)
    for key, value in options.items():
        repo.git.config("--local", key, value)


def active_branch(repo_path: pathlib.Path) -> str:
    """Get the active branch from the given repo.

    Args:
        repo_path: Path to a repo.
    Returns:
        The active branch of the repo.
    """
    return git.Repo(repo_path).active_branch.name


def stash_changes(local_repos: List[plug.StudentRepo]) -> None:
    for repo in local_repos:
        subprocess.run("git stash".split(), cwd=repo.path, capture_output=True)


def git_init(dirpath):
    subprocess.run("git init".split(), cwd=str(dirpath), capture_output=True)
