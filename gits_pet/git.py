"""Wrapper functions for git commands.

This module contains wrapper functions for git commands, such as push and clone.
"""
import os
import subprocess
from typing import Iterable, Tuple

OAUTH_TOKEN = os.getenv('GITS_PET_OAUTH')
if not OAUTH_TOKEN:
    raise OSError('The oauth token is empty!')


def quiet_run(*args, **kwargs):
    """Run a subprocess and pipe output to /dev/null."""
    with open(os.devnull, 'w') as devnull:
        return subprocess.run(
            *args, **kwargs, stdout=devnull, stderr=subprocess.STDOUT)


def captured_run(*args, **kwargs):
    """Run a subprocess and capture the output."""
    return subprocess.run(
        *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_clone(repo_url: str, single_branch: bool = True, branch: str = None):
    """Clone a git repository.

    Args:
        repo_url: HTTPS url to repository on the form https://<host>/<owner>/<repo>.
        single_branch: Whether or not to clone a single branch.
        branch: The branch to clone.
    """
    if not repo_url.startswith('https://'):
        raise ValueError('invalid repo url {}')

    options = []
    if single_branch:
        options.append('--single-branch')
    if branch is not None:
        options += ['-b', branch]
    clone_command = ['git', 'clone', repo_url, *options]
    proc = captured_run(clone_command)
    print(proc.stdout)
    print(proc.stderr)


def git_push(repo_path: str, remote: str = 'origin', branch: str = 'master'):
    """Push a repository. 

    Args:
        repo_path: Path to the root of a git repository.
        remote: Name of the remote to push to.
        branch: Name of the branch to push to.
    """
    pass


def git_add_push_remote(repo_path: str, remotes: Iterable[Tuple[str]]):
    """Add push remotes to a repository.

    Args:
        repo_path: Path to the root of a git repository.
        remotes: A list of (remote, repo_url) pairs to add as push remotes.
    """
    pass
