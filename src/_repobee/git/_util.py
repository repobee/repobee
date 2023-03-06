"""Utility functions that are shared by wrappers defined for git commands.

.. module:: git
    :synopsis: Utility functions that are shared by wrappers defined for git
    commands.
"""

import asyncio
import os
import pathlib
import sys
from typing import Callable, Coroutine, Iterable, Any, Sequence, List, Union

import more_itertools

import repobee_plug as plug
from _repobee import exception


def batch_execution(
    batch_func: Callable[..., Coroutine[Any, None, Any]],
    arg_list: Iterable[Any],
    *batch_func_args,
    **batch_func_kwargs,
) -> Sequence[Exception]:
    """Take a batch function (any function whose first argument is an iterable)
    and send in CONCURRENT_TASKS amount of arguments from the arg_list
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
    loop = _get_event_loop()
    return loop.run_until_complete(
        batch_execution_async(
            batch_func, arg_list, *batch_func_args, **batch_func_kwargs
        )
    )


async def batch_execution_async(
    batch_func: Callable[..., Coroutine[Any, None, Any]],
    arg_list: Iterable[Any],
    *batch_func_args,
    **batch_func_kwargs,
) -> Sequence[Exception]:
    import tqdm.asyncio  # type: ignore

    exceptions = []
    loop = _get_event_loop()
    concurrent_tasks = 20
    for batch, args_chunk in enumerate(
        more_itertools.ichunked(arg_list, concurrent_tasks), start=1
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


def warn_local_repos(local: List[plug.StudentRepo]):
    local_repo_ids = [f"{repo.team.name}/{repo.name}" for repo in local]
    plug.log.warning(
        f"Found local repos, skipping: {', '.join(local_repo_ids)}"
    )


def is_git_repo(path: Union[str, pathlib.Path]) -> bool:
    """Check if a directory has a .git subdirectory.

    Args:
        path: Path to a local directory.
    Returns:
        True if there is a .git subdirectory in the given directory.
    """
    return os.path.isdir(path) and ".git" in os.listdir(path)


def _get_event_loop() -> asyncio.AbstractEventLoop:
    if sys.version_info[:2] < (3, 10):
        return asyncio.get_event_loop()

    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()
