"""Wrapper functions for git commands.

This module contains wrapper functions for git commands, such as push and clone.
"""
import os
import sys
import subprocess
import collections
import daiquiri
import asyncio
from typing import Sequence, Tuple, Iterable

LOGGER = daiquiri.getLogger(__file__)

Push = collections.namedtuple('Push', ('local_path', 'remote_url', 'branch'))


class GitError(Exception):
    """A generic error to raise when a git command exits with a non-zero
    exit status.
    """

    def __init__(self, command: Sequence[str], returncode: int, stderr: bytes):
        msg = ("git exited with a non-zero exit status.{}"
               "issued command: {}{}"
               "return code: {}{}"
               "stderr: {}").format(os.linesep, " ".join(command), os.linesep,
                                    returncode, os.linesep, stderr)
        super().__init__(msg)


class CloneFailedError(GitError):
    """An error to raise when cloning a repository fails."""


class PushFailedError(GitError):
    """An error to raise when pushing to a remote fails."""


OAUTH_TOKEN = os.getenv('GITS_PET_OAUTH')
if not OAUTH_TOKEN:
    raise OSError('The oauth token is empty!')


def _insert_token(https_url: str, token: str = OAUTH_TOKEN) -> str:
    """Insert a token into the https url as described here:
        https://blog.github.com/2012-09-21-easier-builds-and-deployments-using-git-over-https-and-oauth/

    Args:
        https_url: A url on the form `https://host.topdomain`
        token: A GitHub OAUTH token, with or without username (e.g. on the form
        `<token>` or `<username>:<token>`)

    Returns:
        The provided url with the token inserted
    """
    if not https_url.startswith('https://'):
        raise ValueError(
            'invalid url `{}`, does not start with `https://`'.format(
                https_url))
    if not token:
        raise ValueError('invalid token, empty token not allowed')
    return https_url.replace('https://', 'https://{}@'.format(token))


def _insert_user_and_token(https_url: str, user: str,
                           token: str = OAUTH_TOKEN) -> str:
    """Insert a username and an oauth token into the https url as described here:
        https://blog.github.com/2012-09-21-easier-builds-and-deployments-using-git-over-https-and-oauth/

    Args:
        https_url: A url on the form `https://host.topdomain`
        user: A GitHub username.
        token: A GitHub OAUTH token.

    Returns:
        The provided url with the username and token inserted
    """
    return _insert_token(https_url, "{}:{}".format(user, token))


def quiet_run(*args, **kwargs):
    """Run a subprocess and pipe output to /dev/null."""
    with open(os.devnull, 'w') as devnull:
        return subprocess.run(
            *args, **kwargs, stdout=devnull, stderr=subprocess.STDOUT)


def captured_run(*args, **kwargs):
    """Run a subprocess and capture the output."""
    proc = subprocess.run(
        *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode(
        sys.getdefaultencoding()), proc.stderr.decode(sys.getdefaultencoding())


def run_and_log_stderr_realtime(*args, **kwargs):
    """Run a subprocess and capture the output, logging it in real time.."""
    proc = subprocess.Popen(*args, **kwargs, stderr=subprocess.PIPE)

    stderr = []
    while True:
        err = proc.stderr.readline().decode(
            encoding=sys.getdefaultencoding()).rstrip()
        stderr.append(err)
        if not err and proc.poll() is not None:
            break

        LOGGER.info(stderr[-1])
    return proc.poll(), os.linesep.join(stderr)


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
        raise CloneFailedError(clone_command, rc, stderr)


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
    rc, stderr = run_and_log_stderr_realtime(
        push_command, cwd=os.path.abspath(repo_path))

    if rc != 0:
        raise PushFailedError(push_command, rc, stderr)


async def _push_async(repo_path: str,
                      user: str,
                      repo_url: str,
                      branch: str = 'master'):
    """Asynchronous call to git push, pushing directly to the repo_url and branch.


    Args:
        repo_path: Path to the repo ot push.
        user: The username to put on the push.
        repo_url: HTTPS url to the remote repo (without username/token!).
        branch: The branch to push to.
    """
    if not isinstance(repo_path, str):
        raise TypeError(
            'repo_path is of type {.__class__.__name__}, expected str'.format(
                repo_path))
    if not isinstance(user, str):
        raise TypeError(
            'user is of type {.__class__.__name__}, expected str'.format(user))
    if not isinstance(branch, str):
        raise TypeError(
            'branch is of type {.__class__.__name__}, expected str'.format(
                branch))
    if not isinstance(repo_url, str):
        raise TypeError(
            'repo_url is of type {.__class__.__name__}, expected str'.format(
                repo_url))

    if not repo_path:
        raise ValueError("repo_path must not be empty")
    if not user:
        raise ValueError("user must not be empty")
    if not repo_url:
        raise ValueError("repo_url must not be empty")
    if not branch:
        raise ValueError("branch must not be empty")

    loop = asyncio.get_event_loop()

    command = [
        'git', 'push',
        _insert_user_and_token(repo_url, user, OAUTH_TOKEN), branch
    ]
    proc = await asyncio.create_subprocess_exec(*command, cwd=repo_path)
    await proc.communicate()
    if proc.returncode != 0:
        LOGGER.error("Failed to push to {} {}".format(repo_url, branch))
    else:
        LOGGER.info("Pushed files to {} {}".format(repo_url, branch))


Push = collections.namedtuple('Push', ('local_path', 'remote_url', 'branch'))


def push_async(push_tuples: Iterable[Push], user: str):
    """Push to all repos defined in push_tuples.

    Args:
        push_tuples: Push namedtuples defining local and remote repos.
        user: The username to put in the push.
    """
    loop = asyncio.get_event_loop()
    tasks = [
        loop.create_task(
            _push_async(pt.local_path, user, pt.remote_url, pt.branch))
        for pt in push_tuples
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    LOGGER.info("All done!")


def add_push_remotes(repo_path: str, user: str,
                     remotes: Sequence[Sequence[str]]):
    """Add push remotes to a repository.

    Args:
        repo_path: Path to the root of a git repository.
        user: A user associated with the token. Must be added to the remote url
        for pushing without CLI interaction.
        remotes: A list of (remote, repo_url) pairs to add as push remotes.
    """
    if not isinstance(repo_path, str):
        raise TypeError(
            "repo_path is of type {.__class__.__name__}, expected str".format(
                repo_path))
    if not isinstance(user, str):
        raise TypeError(
            "user is of type {.__class__.__name__}, expected str".format(user))
    if not isinstance(remotes, collections.Sequence):
        raise TypeError(
            "remotes is of type {.__class__.__name__}, expected sequence"
            .format(remotes))

    if not repo_path:
        raise ValueError("repo_path must not be empty")
    if not user:
        raise ValueError("user must not be empty")

    bad_pairs = [
        pair for pair in remotes
        if not isinstance(pair, collections.Sequence) or len(pair) != 2
        or not isinstance(pair[0], str) or not isinstance(pair[1], str)
    ]
    if bad_pairs:
        raise ValueError("remotes poorly formed, first bad value: {}".format(
            str(bad_pairs[0])))
    if not remotes:
        raise ValueError("remotes must not be empty")

    for remote, url in remotes:
        url_with_token = _insert_user_and_token(url, user)
        add_remote_command = 'git remote set-url --add --push {} {}'.format(
            remote, url_with_token).split()
        rc, _, stderr = captured_run(
            add_remote_command, cwd=os.path.abspath(repo_path))
        if rc != 0:
            raise GitError(add_remote_command, rc, stderr)
