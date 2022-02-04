"""Wrapper functions for git commands that fetch from remote repository.

.. module:: git
    :synopsis: Wrapper functions for git commands that fetch from remote
    repository, such as fetch, pull, and clone.
"""

import asyncio
import dataclasses
import enum
import pathlib
import shutil
import subprocess
from typing import List, Iterable, Tuple

import repobee_plug as plug
from _repobee import exception, urlutil
from _repobee.git._local import git_init, stash_changes
from _repobee.git._util import batch_execution, warn_local_repos, is_git_repo


@dataclasses.dataclass(frozen=True)
class CloneSpec:
    dest: pathlib.Path
    repo_url: str
    branch: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)


async def _clone_async(clone_spec: CloneSpec):
    """Clone git repositories asynchronously.

    Args:
        clone_spec: A clone specification.
    """
    rc, stderr = await pull_clone_async(clone_spec)

    empty_repo_error = b"fatal: couldn't find remote ref HEAD"
    if rc != 0 and empty_repo_error.lower() not in stderr.lower():
        raise exception.CloneFailedError(
            f"Failed to clone {clone_spec.repo_url}",
            returncode=rc,
            stderr=stderr,
            clone_spec=clone_spec,
        )
    else:
        plug.log.info(f"Cloned into {clone_spec.repo_url}")


async def pull_clone_async(clone_spec: CloneSpec):
    """Simulate a clone with a pull to avoid writing remotes (that could
    include secure tokens) to disk.
    """
    ensure_repo_dir_exists(clone_spec)

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


def ensure_repo_dir_exists(clone_spec: CloneSpec) -> None:
    """Checks if a dir for the repo url exists, and if it does not, creates it.
    Also initializes (or reinitializes, if it already exists) as a git repo.
    """
    if not clone_spec.dest.exists():
        clone_spec.dest.mkdir(parents=True)
    if not is_git_repo(str(clone_spec.dest)):
        git_init(clone_spec.dest)


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
        for exc in batch_execution(_clone_async, clone_specs)
        if isinstance(exc, exception.CloneFailedError)
    ]


def update_local_repos(
    local: List[plug.StudentRepo], api: plug.PlatformAPI
) -> None:
    expected_basedir = local[0].path.parent.parent
    assert all(
        map(lambda repo: repo.path.parent.parent == expected_basedir, local)
    )
    stash_changes(local)
    specs = [
        CloneSpec(repo_url=api.insert_auth(repo.url), dest=repo.path)
        for repo in local
    ]
    # TODO figure out what to do when a local update fails
    clone(specs)


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
        update_local_repos(local, api)
    elif local and not update_local:
        warn_local_repos(local)

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
    process = subprocess.run(command, cwd=cwd, capture_output=True)
    if process.returncode != 0:
        raise exception.CloneFailedError(
            "Failed to clone",
            process.returncode,
            process.stderr,
            CloneSpec(
                repo_url=repo_url,
                dest=pathlib.Path(cwd) / urlutil.extract_repo_name(repo_url),
                branch=branch,
            ),
        )
