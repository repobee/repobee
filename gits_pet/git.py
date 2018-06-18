"""Wrapper functions for git commands.

This module contains wrapper functions for git commands, such as push and clone.
"""
import os
import sys
import subprocess
from typing import Iterable, Tuple


class GitError(RuntimeError):
    """A generic error to raise when a git command exits with a non-zero
    exit status.
    """


class CloneFailedError(GitError):
    """An error to raise when cloning a repository fails."""


class PushFailedError(GitError):
    """An error to raise when pushing to a remote fails."""


OAUTH_TOKEN = os.getenv('GITS_PET_OAUTH')
if not OAUTH_TOKEN:
    raise OSError('The oauth token is empty!')


def _insert_token(https_url: str, token: str = OAUTH_TOKEN) -> str:
    """Insert an oauth token into the https url as described here:
        https://blog.github.com/2012-09-21-easier-builds-and-deployments-using-git-over-https-and-oauth/

    Args:
        https_url: A url on the form `https://host.topdomain`
        token: A GitHub OAUTH token.

    Returns:
        The provided url with the token inserted
    """
    if not https_url.startswith('https://'):
        raise ValueError(
            'invalid url `{}`, does not start with `https://`'.format(
                https_url))
    if not token:
        raise ValueError('invalid token, empty token not allowed')
    return https_url.replace('https://', 'https://{}{}'.format(token, '@'))


def quiet_run(*args, **kwargs):
    """Run a subprocess and pipe output to /dev/null."""
    with open(os.devnull, 'w') as devnull:
        return subprocess.run(
            *args, **kwargs, stdout=devnull, stderr=subprocess.STDOUT)


def captured_run(*args, **kwargs):
    """Run a subprocess and capture the output."""
    proc = subprocess.run(
        *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


def clone(repo_url: str, single_branch: bool = True, branch: str = None):
    """Clone a git repository.

    Args:
        repo_url: HTTPS url to repository on the form https://<host>/<owner>/<repo>.
        single_branch: Whether or not to clone a single branch.
        branch: The branch to clone.
    """
    if not isinstance(repo_url, str):
        raise TypeError(
            'repo_url is of type {.__class__.__name__}, expected str'.format(
                repo_url))
    if not isinstance(single_branch, bool):
        raise TypeError(
            'single_branch is of type {.__class__.__name__}, expected bool'.
            format(single_branch))
    if not isinstance(branch, (type(None), str)):
        raise TypeError(
            'branch is of type {.__class__.__name__}, expected NoneType or str'
        )

    if isinstance(branch, str) and not branch:
        raise ValueError("branch must not be empty")

    options = []
    if single_branch:
        options.append('--single-branch')
    if branch is not None:
        options += ['-b', branch]

    clone_command = [
        'git', 'clone',
        _insert_token(repo_url, OAUTH_TOKEN), *options
    ]
    rc, _, stderr = captured_run(clone_command)

    if rc != 0:
        msg = ("git exited with a non-zero exit status.{}"
               "issued command: {}{}"
               "return code: {}{}"
               "stderr: {}").format(
                   os.linesep,
                   " ".join(clone_command),
                   os.linesep,
                   rc,
                   os.linesep,
                   stderr.decode(encoding=sys.getdefaultencoding()))
        raise CloneFailedError(msg)


def push(repo_path: str, remote: str = 'origin', branch: str = 'master'):
    """Push a repository. 

    Args:
        repo_path: Path to the root of a git repository.
        remote: Name of the remote to push to.
        branch: Name of the branch to push to.
    """
    if not isinstance(repo_path, str):
        raise TypeError(
            'repo_path is of type {.__class__.__name__}, expected str'.format(
                repo_path))
    if not isinstance(remote, str):
        raise TypeError(
            'remote is of type {.__class__.__name__}, expected str'.format(
                remote))
    if not isinstance(branch, str):
        raise TypeError(
            'branch is of type {.__class__.__name__}, expected str'.format(
                branch))

    if not repo_path:
        raise ValueError("repo_path must not be empty")
    if not remote:
        raise ValueError("remote must not be empty")
    if not branch:
        raise ValueError("branch must not be empty")

    push_command = ['git', 'push', remote, branch]
    rc, _, stderr = captured_run(push_command, cwd=os.path.abspath(repo_path))

    if rc != 0:
        msg = ("git exited with a non-zero exit status.{}"
               "issued command: {}{}"
               "return code: {}{}"
               "stderr: {}").format(
                   os.linesep,
                   " ".join(push_command),
                   os.linesep,
                   rc,
                   os.linesep,
                   stderr.decode(encoding=sys.getdefaultencoding()))
        raise PushFailedError(msg)


def add_push_remote(repo_path: str, remotes: Iterable[Tuple[str]]):
    """Add push remotes to a repository.

    Args:
        repo_path: Path to the root of a git repository.
        remotes: A list of (remote, repo_url) pairs to add as push remotes.
    """
    pass
