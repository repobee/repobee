"""Wrapper functions for git commands.

.. module:: git
    :synopsis: Wrapper functions for git CLI commands, such as push and clone.

.. moduleauthor:: Simon Larsén
"""
import asyncio
import os
import subprocess
import collections
import pathlib
import daiquiri
from typing import Iterable, List, Any, Callable

from _repobee import exception
from _repobee import util

CONCURRENT_TASKS = 20

LOGGER = daiquiri.getLogger(__file__)

Push = collections.namedtuple("Push", ("local_path", "repo_url", "branch"))


def _ensure_repo_dir_exists(repo_url: str, cwd: str) -> pathlib.Path:
    """Checks if a dir for the repo url exists, and if it does not, creates it.
    Also initializez (or reinitializes, if it alrady exists) as a git repo.
    """
    repo_name = util.repo_name(repo_url)
    dirpath = pathlib.Path(cwd) / repo_name
    if not dirpath.exists():
        dirpath.mkdir()
    _git_init(dirpath)
    return dirpath


def _git_init(dirpath):
    captured_run(["git", "init"], cwd=str(dirpath))


def _pull_clone(repo_url: str, branch: str = "", cwd: str = "."):
    """Simulate a clone with a pull to avoid writing remotes (that could
    include secure tokens) to disk.
    """
    dirpath = _ensure_repo_dir_exists(repo_url, cwd)

    pull_command = "git pull {} {}".format(repo_url, branch).strip().split()

    rc, _, stderr = captured_run(pull_command, cwd=str(dirpath))
    return rc, stderr


async def _pull_clone_async(repo_url: str, branch: str = "", cwd: str = "."):
    """Same as _pull_clone, but asynchronously."""
    dirpath = _ensure_repo_dir_exists(repo_url, cwd)

    pull_command = "git pull {} {}".format(repo_url, branch).strip().split()

    proc = await asyncio.create_subprocess_exec(
        *pull_command,
        cwd=str(dirpath),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    return proc.returncode, stderr


def captured_run(*args, **kwargs):
    """Run a subprocess and capture the output."""
    proc = subprocess.run(
        *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return proc.returncode, proc.stdout, proc.stderr


def clone_single(repo_url: str, branch: str = "", cwd: str = "."):
    """Clone a git repository.

    Args:
        repo_url: HTTPS url to repository on the form
            https://<host>/<owner>/<repo>.
        branch: The branch to clone.
        cwd: Working directory. Defaults to the current directory.
    """
    rc, stderr = _pull_clone(repo_url, branch, cwd)
    if rc != 0:
        raise exception.CloneFailedError(
            "Failed to clone", rc, stderr, repo_url
        )


async def _clone_async(repo_url: str, branch: str = "", cwd="."):
    """Clone git repositories asynchronously.

    Args:
        repo_url: A url to clone.
        branch: Which branch to clone.
        cwd: Working directory.
    """
    rc, stderr = await _pull_clone_async(repo_url, branch, cwd)

    if rc != 0:
        raise exception.CloneFailedError(
            "Failed to clone {}".format(repo_url),
            returncode=rc,
            stderr=stderr,
            url=repo_url,
        )
    else:
        LOGGER.info("Cloned into {}".format(repo_url))


def clone(repo_urls: Iterable[str], cwd: str = ".") -> List[Exception]:
    """Clone all repos asynchronously.

    Args:
        repo_urls: URLs to repos to clone.
        cwd: Working directory. Defaults to the current directory.

    Returns:
        URLs from which cloning failed.
    """
    # TODO valdate repo_urls
    return [
        exc.url
        for exc in _batch_execution(_clone_async, repo_urls, cwd=cwd)
        if isinstance(exc, exception.CloneFailedError)
    ]


async def _push_async(pt: Push):
    """Asynchronous call to git push, pushing directly to the repo_url and branch.

    Args:
        pt: A Push namedtuple.
    """
    command = ["git", "push", pt.repo_url, pt.branch]
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=os.path.abspath(pt.local_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise exception.PushFailedError(
            "Failed to push to {}".format(pt.repo_url),
            proc.returncode,
            stderr,
            pt.repo_url,
        )
    elif b"Everything up-to-date" in stderr:
        LOGGER.info("{} is up-to-date".format(pt.repo_url))
    else:
        LOGGER.info("Pushed files to {} {}".format(pt.repo_url, pt.branch))


def _push_no_retry(push_tuples: Iterable[Push]) -> List[str]:
    """Push to all repos defined in push_tuples asynchronously. Amount of
    concurrent tasks is limited by CONCURRENT_TASKS.

    Pushes once and only once to each repo.

    Args:
        push_tuples: Push namedtuples defining local and remote repos.

    Returns:
        urls to which pushes failed with exception.PushFailedError. Other
        errors are only logged.
    """
    return [
        exc.url
        for exc in _batch_execution(_push_async, push_tuples)
        if isinstance(exc, exception.PushFailedError)
    ]


def push(push_tuples: Iterable[Push], tries: int = 3) -> List[str]:
    """Push to all repos defined in push_tuples asynchronously. Amount of
    concurrent tasks is limited by CONCURRENT_TASKS. Pushing to repos is tried
    a maximum of ``tries`` times (i.e. pushing is _retried_ ``tries - 1``
    times.)

    Args:
        push_tuples: Push namedtuples defining local and remote repos.
        tries: Amount of times to try to push (including initial push).

    Returns:
        urls to which pushes failed with exception.PushFailedError. Other
        errors are only logged.
    """
    if tries < 1:
        raise ValueError("tries must be larger than 0")
    # confusing, but failed_pts needs an initial value
    failed_pts = list(push_tuples)
    for i in range(tries):
        LOGGER.info("Pushing, attempt {}/{}".format(i + 1, tries))
        failed_urls = set(_push_no_retry(failed_pts))
        failed_pts = [pt for pt in push_tuples if pt.repo_url in failed_urls]
        if not failed_pts:
            break
        LOGGER.warning("{} pushes failed ...".format(len(failed_pts)))

    return [pt.repo_url for pt in failed_pts]


def _batch_execution(
    batch_func: Callable[[Iterable[Any], Any], List[asyncio.Task]],
    arg_list: Iterable[Any],
    *batch_func_args,
    **batch_func_kwargs
) -> List[Exception]:
    """Take a batch function (any function whos first argument is an iterable)
    and send in send in CONCURRENT_TASKS amount of arguments from the arg_list
    until it is exhausted. The batch_func_kwargs are provided on each call.

    Args:
        batch_func: A function that takes an iterable as a first argument and
            returns
        a list of asyncio.Task objects.
        arg_list: A list of objects that are of the same type as the
        batch_func's first argument.
        batch_func_kwargs: Additional keyword arguments to the batch_func.

    Returns:
        a list of exceptions raised in the tasks returned by the batch
        function.
    """
    completed_tasks = []
    args_iter = iter(arg_list)

    loop = asyncio.get_event_loop()
    has_more_jobs = True
    while has_more_jobs:
        args = []
        for _ in range(CONCURRENT_TASKS):
            try:
                args.append(next(args_iter))
            except StopIteration:
                has_more_jobs = False

        tasks = [
            loop.create_task(
                batch_func(arg, *batch_func_args, **batch_func_kwargs)
            )
            for arg in args
        ]
        # if
        # a) arg_list was empty
        # or
        # b) len(arg_list) % CONCURRENT_TASKS == 0
        # the last iteration will have no tasks
        if tasks:
            loop.run_until_complete(asyncio.wait(tasks))
            completed_tasks += tasks

    exceptions = [
        task.exception() for task in completed_tasks if task.exception()
    ]
    for exc in exceptions:
        LOGGER.error(str(exc))

    return exceptions
