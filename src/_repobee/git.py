"""Wrapper functions for git commands.

.. module:: git
    :synopsis: Wrapper functions for git CLI commands, such as push and clone.

.. moduleauthor:: Simon Larsén
"""
import asyncio
import enum
import os
import pathlib
import shutil
import subprocess
import sys
import dataclasses
from typing import (
    Iterable,
    List,
    Any,
    Callable,
    Tuple,
    Awaitable,
    Sequence,
    Mapping,
)

import more_itertools
import git  # type: ignore

import repobee_plug as plug

from _repobee import exception
from _repobee import util

CONCURRENT_TASKS = 20


@dataclasses.dataclass(frozen=True)
class Push:
    local_path: pathlib.Path
    repo_url: str
    branch: str
    metadata: dict = dataclasses.field(default_factory=dict)

    def __iter__(self):
        """Iter implementation just to make this dataclass unpackable."""
        return iter((self.local_path, self.repo_url, self.branch))


@dataclasses.dataclass(frozen=True)
class CloneSpec:
    dest: pathlib.Path
    repo_url: str
    branch: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)


_EMPTY_REPO_ERROR = b"""fatal: Couldn't find remote ref HEAD"""


def _ensure_repo_dir_exists(clone_spec: CloneSpec) -> None:
    """Checks if a dir for the repo url exists, and if it does not, creates it.
    Also initializez (or reinitializes, if it alrady exists) as a git repo.
    """
    if not clone_spec.dest.exists():
        clone_spec.dest.mkdir(parents=True)
    if not util.is_git_repo(str(clone_spec.dest)):
        _git_init(clone_spec.dest)


def _git_init(dirpath):
    captured_run(["git", "init"], cwd=str(dirpath))


async def _pull_clone_async(clone_spec: CloneSpec):
    """Simulate a clone with a pull to avoid writing remotes (that could
    include secure tokens) to disk.
    """
    _ensure_repo_dir_exists(clone_spec)

    pull_command = (
        f"git pull {clone_spec.repo_url} "
        f"{clone_spec.branch or ''}".strip().split()
    )

    proc = await asyncio.create_subprocess_exec(
        *pull_command,
        cwd=str(clone_spec.dest),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
    """Clone a git repository with ``git clone``.

    This should only be used for temporary cloning, as any secure tokens in the
    repo URL are stored in the repository.

    Args:
        repo_url: HTTPS url to repository on the form
            https://<host>/<owner>/<repo>.
        branch: The branch to clone.
        cwd: Working directory. Defaults to the current directory.
    """
    command = [*"git clone --single-branch".split(), repo_url] + (
        [branch] if branch else []
    )
    rc, _, stderr = captured_run(command, cwd=cwd)
    if rc != 0:
        raise exception.CloneFailedError(
            "Failed to clone",
            rc,
            stderr,
            CloneSpec(
                repo_url=repo_url,
                dest=pathlib.Path(cwd) / util.repo_name(repo_url),
                branch=branch,
            ),
        )


async def _clone_async(clone_spec: CloneSpec):
    """Clone git repositories asynchronously.

    Args:
        clone_spec: A clone specification.
    """
    rc, stderr = await _pull_clone_async(clone_spec)

    if rc != 0 and _EMPTY_REPO_ERROR not in stderr:
        raise exception.CloneFailedError(
            f"Failed to clone {clone_spec.repo_url}",
            returncode=rc,
            stderr=stderr,
            clone_spec=clone_spec,
        )
    else:
        plug.log.info(f"Cloned into {clone_spec.repo_url}")


class CloneStatus(enum.Enum):
    CLONED = enum.auto()
    EXISTED = enum.auto()
    FAILED = enum.auto()


def clone_student_repos(
    repos: List[plug.StudentRepo],
    clone_dir: pathlib.Path,
    update_local: bool,
    api: plug.PlatformAPI,
) -> Iterable[Tuple[CloneStatus, plug.StudentRepo]]:
    assert all(map(lambda r: r.path is not None, repos))
    local = [repo for repo in repos if repo.path.exists()]
    if local and update_local:
        _update_local_repos(local, api)
    elif local and not update_local:
        _warn_local_repos(local)

    non_local = [repo for repo in repos if not repo.path.exists()]
    plug.log.info(f"Cloning into {non_local}")
    non_local_specs = [
        CloneSpec(
            dest=clone_dir / plug.fileutils.hash_path(repo.path),
            repo_url=api.insert_auth(repo.url),
            metadata=dict(repo=repo),
        )
        for repo in non_local
    ]

    failed_specs = clone(non_local_specs)

    failed_repos = {spec.metadata["repo"] for spec in failed_specs}
    success_repos = {repo for repo in non_local if repo not in failed_repos}

    for repo in success_repos:
        shutil.copytree(
            src=clone_dir / plug.fileutils.hash_path(repo.path), dst=repo.path
        )

    return (
        [(CloneStatus.EXISTED, repo) for repo in local]
        + [(CloneStatus.CLONED, repo) for repo in success_repos]
        + [(CloneStatus.FAILED, repo) for repo in failed_repos]
    )


def _warn_local_repos(local: List[plug.StudentRepo],):
    local_repo_ids = [f"{repo.team.name}/{repo.name}" for repo in local]
    plug.log.warning(
        f"Found local repos, skipping: {', '.join(local_repo_ids)}"
    )


def _update_local_repos(
    local: List[plug.StudentRepo], api: plug.PlatformAPI
) -> None:
    expected_basedir = local[0].path.parent.parent
    assert all(
        map(lambda repo: repo.path.parent.parent == expected_basedir, local)
    )
    _stash_changes(local)
    specs = [
        CloneSpec(repo_url=api.insert_auth(repo.url), dest=repo.path)
        for repo in local
    ]
    # TODO figure out what to do when a local update fails
    clone(specs)


def _stash_changes(local_repos: List[plug.StudentRepo]) -> None:
    for repo in local_repos:
        captured_run("git stash".split(), cwd=repo.path)


def clone(clone_specs: Iterable[CloneSpec]) -> List[CloneSpec]:
    """Clone all repos asynchronously.

    Args:
        clone_specs: Clone specifications for repos to clone.
        cwd: Working directory. Defaults to the current directory.

    Returns:
        Specs for which the cloning failed.
    """
    return [
        exc.clone_spec
        for exc in _batch_execution(_clone_async, clone_specs)
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
        stderr=subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise exception.PushFailedError(
            f"Failed to push to {pt.repo_url}",
            proc.returncode or -sys.maxsize,
            stderr,
            pt.repo_url,
        )
    elif b"Everything up-to-date" in stderr:
        plug.log.info(f"{pt.repo_url} is up-to-date")
    else:
        plug.log.info(f"Pushed files to {pt.repo_url} {pt.branch}")


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


def push(
    push_tuples: Iterable[Push], tries: int = 3
) -> Tuple[List[Push], List[Push]]:
    """Push to all repos defined in push_tuples asynchronously. Amount of
    concurrent tasks is limited by CONCURRENT_TASKS. Pushing to repos is tried
    a maximum of ``tries`` times (i.e. pushing is _retried_ ``tries - 1``
    times.)

    Args:
        push_tuples: Push namedtuples defining local and remote repos.
        tries: Amount of times to try to push (including initial push).

    Returns:
        A tuple of lists of push tuples on the form (successful, failures).
    """
    if tries < 1:
        raise ValueError("tries must be larger than 0")

    push_tuples = list(push_tuples)
    # confusing, but failed_pts needs an initial value
    failed_pts = list(push_tuples)
    for i in range(tries):
        plug.log.info(f"Pushing, attempt {i + 1}/{tries}")
        failed_urls = set(_push_no_retry(failed_pts))
        failed_pts = [pt for pt in failed_pts if pt.repo_url in failed_urls]
        if not failed_pts:
            break
        plug.log.warning(f"{len(failed_pts)} pushes failed ...")

    successful_pts = [pt for pt in push_tuples if pt not in failed_pts]
    return successful_pts, failed_pts


def _batch_execution(
    batch_func: Callable[..., Awaitable],
    arg_list: Iterable[Any],
    *batch_func_args,
    **batch_func_kwargs,
) -> Sequence[Exception]:
    """Take a batch function (any function whos first argument is an iterable)
    and send in send in CONCURRENT_TASKS amount of arguments from the arg_list
    until it is exhausted. The batch_func_kwargs are provided on each call.

    Args:
        batch_func: A function that takes an iterable as a first argument and
            returns a list of asyncio.Task objects.
        arg_list: A list of objects that are of the same type as the
        batch_func's first argument.
        batch_func_kwargs: Additional keyword arguments to the batch_func.

    Returns:
        a list of exceptions raised in the tasks returned by the batch
        function.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _batch_execution_async(
            batch_func, arg_list, *batch_func_args, **batch_func_kwargs
        )
    )


async def _batch_execution_async(
    batch_func: Callable[..., Awaitable],
    arg_list: Iterable[Any],
    *batch_func_args,
    **batch_func_kwargs,
) -> Sequence[Exception]:

    import tqdm.asyncio  # type: ignore

    exceptions = []
    loop = asyncio.get_event_loop()
    for batch, args_chunk in enumerate(
        more_itertools.ichunked(arg_list, CONCURRENT_TASKS), start=1
    ):
        tasks = [
            loop.create_task(
                batch_func(arg, *batch_func_args, **batch_func_kwargs)
            )
            for arg in args_chunk
        ]
        for coro in tqdm.asyncio.tqdm_asyncio.as_completed(
            tasks, desc=f"Progress batch {batch}", file=sys.stdout
        ):
            try:
                await coro
            except exception.GitError as exc:
                exceptions.append(exc)

    for e in exceptions:
        plug.log.error(str(e))

    return exceptions


def active_branch(repo_path: pathlib.Path) -> str:
    """Get the active branch from the given repo.

    Args:
        repo_path: Path to a repo.
    Returns:
        The active branch of the repo.
    """
    return git.Repo(repo_path).active_branch.name


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
