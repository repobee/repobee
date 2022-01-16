"""Wrapper functions for git commands that push to remote repository.

.. module:: git
    :synopsis: Wrapper functions for git commands that push to remote
    repository.
"""

import asyncio
import dataclasses
import os
import pathlib
import subprocess
import sys
from typing import Iterable, List, Tuple

import repobee_plug as plug
from _repobee import exception
from _repobee.git._util import batch_execution


@dataclasses.dataclass(frozen=True)
class PushSpec:
    local_path: pathlib.Path
    repo_url: str
    branch: str
    metadata: dict = dataclasses.field(default_factory=dict)

    def __iter__(self):
        """Iter implementation just to make this dataclass unpackable."""
        return iter((self.local_path, self.repo_url, self.branch))


async def _push_async(pt: PushSpec):
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


def push(
    push_tuples: Iterable[PushSpec], tries: int = 3
) -> Tuple[List[PushSpec], List[PushSpec]]:
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
        failed_urls = set(push_no_retry(failed_pts))
        failed_pts = [pt for pt in failed_pts if pt.repo_url in failed_urls]
        if not failed_pts:
            break
        plug.log.warning(f"{len(failed_pts)} pushes failed ...")

    successful_pts = [pt for pt in push_tuples if pt not in failed_pts]
    return successful_pts, failed_pts


def push_no_retry(push_tuples: Iterable[PushSpec]) -> List[str]:
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
        for exc in batch_execution(_push_async, push_tuples)
        if isinstance(exc, exception.PushFailedError)
    ]
