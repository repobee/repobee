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


def _validate_types(**kwargs):
    r"""Validate argument types. Raise TypeError if there is a mismatch.
    
    Args:
        **kwargs: Mapping on the form {param_name: (argument, expected_type)},
        where param_name is the name of the parameter, argument is the passed
        in value and expected type is either a single type, or a tuple of
        types.
    """
    for param_name, (argument, expected_types) in kwargs.items():
        if not isinstance(argument, expected_types):
            if isinstance(expected_types, tuple):
                exp_type_str = " or ".join(
                    [t.__name__ for t in expected_types])
            else:
                exp_type_str = expected_types.__name__
            raise TypeError(
                "{} is of type {.__class__.__name__}, expected {}".format(
                    param_name, argument, exp_type_str))


def clone(repo_url: str, single_branch: bool = True, branch: str = None):
    """Clone a git repository.

    Args:
        repo_url: HTTPS url to repository on the form https://<host>/<owner>/<repo>.
        single_branch: Whether or not to clone a single branch.
        branch: The branch to clone.
    """
    _validate_types(
        repo_url=(repo_url, str),
        single_branch=(single_branch, bool),
        branch=(branch, (str, type(None))))

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


async def _push_async(local_repo: str,
                      user: str,
                      repo_url: str,
                      branch: str = 'master'):
    """Asynchronous call to git push, pushing directly to the repo_url and branch.

    Args:
        local_repo: Path to the repo to push.
        user: The username to put on the push.
        repo_url: HTTPS url to the remote repo (without username/token!).
        branch: The branch to push to.
    """
    _validate_types(
        local_repo=(local_repo, str),
        user=(user, str),
        repo_url=(repo_url, str),
        branch=(branch, str))

    if not local_repo:
        raise ValueError("local_repo must not be empty")
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
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=os.path.abspath(local_repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise PushFailedError(command, proc.returncode, stderr)
    elif b"Everything up-to-date" in stderr:
        LOGGER.info("{} is up-to-date".format(repo_url))
    else:
        LOGGER.info("Pushed files to {} {}".format(repo_url, branch))


def push(local_repo: str, user: str, repo_url: str, branch: str = 'master'):
    """Push from a local repository to a remote repository without first adding
    push remotes.

    Args:
        local_repo: Path to the repo to push.
        user: The username to put on the push.
        repo_url: HTTPS url to the remote repo (without username/token!).
        branch: The branch to push to.
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(_push_async(local_repo, user, repo_url, branch))
    loop.run_until_complete(task)
    if task.exception():
        pass
        #raise task.exception()


def push_many(push_tuples: Iterable[Push], user: str):
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
