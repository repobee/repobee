"""Helper functions for tests."""
import tempfile
import pathlib
import shutil
from typing import Mapping, List

import repobee
import git

from repobee_plug.testhelpers import fakeapi
from repobee_plug.testhelpers import const


def initialize_repo(path: pathlib.Path) -> git.Repo:
    """Initialize the directory to a Git repo and commit all files in it.
    """
    repo = git.Repo.init(path)
    repo.git.add(".", "--force")
    repo.git.commit("-m", "Initial commit")
    return repo


def hash_directory(dirpath: pathlib.Path) -> str:
    """Compute the directory hash using Git.

    Args:
        dirpath: Path to a directory.
    Returns:
        The hash of the root tree of the directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = pathlib.Path(tmpdir) / "repo"
        shutil.copytree(dirpath, target_dir)
        repo = initialize_repo(target_dir)
        return repo.head.commit.tree.hexsha


def run_repobee(cmd: str, **kwargs):
    """Helper function to call repobee.run.

    Note that ``cmd`` should be a string, and not a list of strings.
    """
    plugins = (kwargs.get("plugins") or []) + [fakeapi]
    kwargs["plugins"] = plugins
    repobee.run(cmd.split(), **kwargs)


def template_repo_hashes() -> Mapping[str, str]:
    """Get hashes for the template repos.

    Returns:
        A mapping (template_repo_name -> hash)
    """
    return {
        path.name: hash_directory(path)
        for path in map(
            lambda name: const.TEMPLATE_REPO_DIR / name,
            const.TEMPLATE_REPO_NAMES,
        )
    }


def tree_hash(repo_root: pathlib.Path) -> str:
    """Get the hash of the HEAD tree object of this repository.

    Args:
        repo_root: Path to the root of a Git repository.
    Returns:
        The hash of the root tree object.
    """
    repo = git.Repo(repo_root)
    return repo.head.commit.tree.hexsha


def get_repos(
    platform_url: str, org_name: str = const.TARGET_ORG_NAME
) -> List[fakeapi.Repo]:
    """Get all repos from the given platform and organization.

    Args:
        platform_url: URL to the directory used by the
            :py:class:`fakeapi.FakeAPI`.
        org_name: The organization to get repos from.
    Returns:
        A list of fake repos.
    """
    api = fakeapi.FakeAPI(
        base_url=platform_url, user=const.TEACHER, org_name=org_name
    )
    return api._repos[org_name].values()


def get_teams(platform_url: str, org_name: str) -> List[fakeapi.Team]:
    """Get all of the teams form the given platform and organization.

    Args:
        platform_url: URL to the directory used by the
            :py:class:`fakeapi.FakeAPI`.
        org_name: The organization to get repos from.
    Returns:
        A list of fake teams.
    """
    api = fakeapi.FakeAPI(
        base_url=platform_url, user=const.TEACHER, org_name=org_name
    )
    return api._teams[org_name].values()
