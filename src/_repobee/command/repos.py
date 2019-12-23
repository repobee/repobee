"""Top-level commands for working with repos.

This module contains high level functions for administrating repositories, such
as creating student repos from some master repo template. All functions follow
the conventions specified in :ref:`conventions`.

Each public function in this module is to be treated as a self-contained
program.

.. module:: repos
    :synopsis: Top-level commands for working with repos.

.. moduleauthor:: Simon Larsén
"""
import itertools
import pathlib
import shutil
import os
import sys
import tempfile
from typing import Iterable, List, Optional, Mapping, Generator

import daiquiri

import repobee_plug as plug

from _repobee import git
from _repobee import util
from _repobee import exception
from _repobee import config
from _repobee import constants
from _repobee import plugin
from _repobee.git import Push

LOGGER = daiquiri.getLogger(__file__)


def setup_student_repos(
    master_repo_urls: Iterable[str], teams: Iterable[plug.Team], api: plug.API
) -> Mapping[str, List[plug.Result]]:
    """Setup student repositories based on master repo templates. Performs three
    primary tasks:

        1. Create the specified teams on the target platform and add the
        specified members to their teams. If a team already exists, it is left
        as-is. If a student is already in a team they are assigned to, nothing
        happens. If no account exists for some specified username, that
        particular student is ignored, but any associated teams are still
        created (even if a missing user is the only member of that team).

        2. For each master repository, create one student repo per team and add
        it to the corresponding student team. If a repository already exists,
        it is skipped.

        3. Push files from the master repos to the corresponding student repos.

    Args:
        master_repo_urls: URLs to master repos.
        teams: An iterable of student teams specifying the teams to be setup.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    urls = list(master_repo_urls)  # safe copy
    master_repo_names = [util.repo_name(url) for url in urls]

    with tempfile.TemporaryDirectory() as tmpdir:
        LOGGER.info("Cloning into master repos ...")
        master_repo_paths = _clone_all(urls, cwd=tmpdir)
        hook_results = plugin.execute_setup_tasks(
            master_repo_names, api, cwd=pathlib.Path(tmpdir)
        )

        teams = api.ensure_teams_and_members(teams)
        repo_urls = _create_student_repos(urls, teams, api)

        push_tuples = _create_push_tuples(master_repo_paths, repo_urls)
        LOGGER.info("Pushing files to student repos ...")
        git.push(push_tuples)

    return hook_results


def _create_student_repos(
    master_repo_urls: Iterable[str], teams: Iterable[plug.Team], api: plug.API
) -> List[str]:
    """Create student repos. Each team is assigned a single repo per master
    repo. Repos that already exist are not created, but their urls are returned
    all the same.

    Args:
        master_repo_urls: URLs to master repos.
        teams: An iterable of student teams specifying the teams to be setup.
        api: An implementation of :py:class:`plug.API` used to interface
            with the platform (e.g. GitHub or GitLab) instance.
    Returns:
        a list of urls to the repos
    """
    LOGGER.info("Creating student repos ...")
    repo_infos = _create_repo_infos(master_repo_urls, teams)
    repo_urls = api.create_repos(repo_infos)
    return repo_urls


def _clone_all(urls: Iterable[str], cwd: str):
    """Attempts to clone all urls, sequentially. If a repo is already present,
    it is skipped.  If any one clone fails (except for fails because the repo
    is local), all cloned repos are removed

    Args:
        urls: HTTPS urls to git repositories.
        cwd: Working directory. Use temporary directory for automatic cleanup.
    Returns:
        local paths to the cloned repos.
    """
    if len(set(urls)) != len(urls):
        raise ValueError("master_repo_urls contains duplicates")
    try:
        for url in urls:
            LOGGER.info("Cloning into {}".format(url))
            git.clone_single(url, cwd=cwd)
    except exception.CloneFailedError:
        LOGGER.error("Error cloning into {}, aborting ...".format(url))
        raise
    paths = [os.path.join(cwd, util.repo_name(url)) for url in urls]
    assert all(map(util.is_git_repo, paths)), "all repos must be git repos"
    return paths


def update_student_repos(
    master_repo_urls: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.API,
    issue: Optional[plug.Issue] = None,
) -> Mapping[str, List[plug.Result]]:
    """Attempt to update all student repos related to one of the master repos.

    Args:
        master_repo_urls: URLs to master repos. Must be in the organization
            that the api is set up for.
        teams: An iterable of student teams.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
        issue: An optional issue to open in repos to which pushing fails.
    """
    urls = list(master_repo_urls)  # safe copy

    if len(set(urls)) != len(urls):
        raise ValueError("master_repo_urls contains duplicates")

    master_repo_names = [util.repo_name(url) for url in urls]

    repo_urls = api.get_repo_urls(master_repo_names, teams=teams)

    with tempfile.TemporaryDirectory() as tmpdir:
        LOGGER.info("Cloning into master repos ...")
        master_repo_paths = _clone_all(urls, tmpdir)
        hook_results = plugin.execute_setup_tasks(
            master_repo_names, api, cwd=pathlib.Path(tmpdir)
        )

        push_tuples = _create_push_tuples(master_repo_paths, repo_urls)

        LOGGER.info("Pushing files to student repos ...")
        failed_urls = git.push(push_tuples)

    if failed_urls and issue:
        LOGGER.info("Opening issue in repos to which push failed")
        _open_issue_by_urls(failed_urls, issue, api)

    LOGGER.info("Done!")
    return hook_results


def _open_issue_by_urls(
    repo_urls: Iterable[str], issue: plug.Issue, api: plug.API
) -> None:
    """Open issues in the repos designated by the repo_urls.

    Args:
        repo_urls: URLs to repos in which to open an issue.
        issue: An issue to open.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_names = [util.repo_name(url) for url in repo_urls]
    api.open_issue(issue.title, issue.body, repo_names)


def clone_repos(
    repos: Iterable[plug.Repo], api: plug.API
) -> Mapping[str, List[plug.Result]]:
    """Clone all student repos related to the provided master repos and student
    teams.

    Args:
        repos: The repos to be cloned. This function does not use the
            ``implementation`` attribute, so it does not need to be set.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    Returns:
        A mapping from repo name to a list of hook results.
    """
    repos_for_tasks, repos_for_clone = itertools.tee(repos)
    non_local_repos = _non_local_repos(repos_for_clone)

    LOGGER.info("Cloning into student repos ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        _clone_repos_no_check(non_local_repos, tmpdir, api)

    for p in plug.manager.get_plugins():
        if "act_on_cloned_repo" in dir(p) or "clone_task" in dir(p):
            return plugin.execute_clone_tasks(
                [repo.name for repo in repos_for_tasks], api
            )
    return {}


def _non_local_repos(
    repos, cwd=pathlib.Path(".")
) -> Generator[plug.Repo, None, None]:
    """Yield repos with names that do not clash with any of the files present
    in cwd.
    """
    local_files = set(path.name for path in cwd.glob("*"))
    for repo in repos:
        if repo.name not in local_files:
            yield repo
        else:
            LOGGER.warning("{} already on disk, skipping".format(repo.name))


def _clone_repos_no_check(repos, dst_dirpath, api) -> List[str]:
    """Clone the specified repo urls into the destination directory without
    making any sanity checks; they must be done in advance.

    Return a list of names of the successfully cloned repos.
    """
    repos_iter_a, repos_iter_b = itertools.tee(repos)
    repo_urls = (repo.url for repo in repos_iter_b)

    fail_urls = git.clone(repo_urls, cwd=dst_dirpath)
    fail_repo_names = set(api.extract_repo_name(url) for url in fail_urls)
    repo_names = set(repo.name for repo in repos_iter_a)
    cloned_repos = [
        path
        for path in pathlib.Path(dst_dirpath).iterdir()
        if path.is_dir()
        and util.is_git_repo(str(path))
        and path.name not in fail_repo_names
        and path.name in repo_names
    ]

    cur_dir = pathlib.Path(".").resolve()
    for repo in cloned_repos:
        shutil.copytree(src=str(repo), dst=str(cur_dir / repo.name))
    return [repo.name for repo in cloned_repos]


def migrate_repos(master_repo_urls: Iterable[str], api: plug.API) -> None:
    """Migrate a repository from an arbitrary URL to the target organization.
    The new repository is added to the master_repos team, which is created if
    it does not already exist.

    Args:
        master_repo_urls: HTTPS URLs to the master repos to migrate.
            the username that is used in the push.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    master_names = [util.repo_name(url) for url in master_repo_urls]

    infos = [
        plug.Repo(
            name=master_name,
            description="Master repository {}".format(master_name),
            private=True,
        )
        for master_name in master_names
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        _clone_all(master_repo_urls, cwd=tmpdir)
        repo_urls = api.create_repos(infos)

        git.push(
            [
                git.Push(
                    local_path=os.path.join(tmpdir, info.name),
                    repo_url=repo_url,
                    branch="master",
                )
                for repo_url, info in zip(repo_urls, infos)
            ]
        )

    LOGGER.info("Done!")


def _create_repo_infos(
    urls: Iterable[str], teams: Iterable[plug.Team]
) -> List[plug.Repo]:
    """Create Repo namedtuples for all combinations of url and team.

    Args:
        urls: Master repo urls.
        teams: Team namedtuples.

    Returns:
        A list of Repo namedtuples with all (url, team) combinations.
    """
    repo_infos = []
    for url in urls:
        repo_base_name = util.repo_name(url)
        repo_infos += [
            plug.Repo(
                name=plug.generate_repo_name(team.name, repo_base_name),
                description="{} created for {}".format(
                    repo_base_name, team.name
                ),
                private=True,
                team_id=team.id,
            )
            for team in teams
        ]
    return repo_infos


def _create_push_tuples(
    master_repo_paths: Iterable[str], repo_urls: Iterable[str]
) -> List[Push]:
    """Create Push namedtuples for all repo urls in repo_urls that share
    repo base name with any of the urls in master_urls.

    Args:
        master_repo_paths: Local paths to master repos.
        repo_urls: Urls to student repos.

    Returns:
        A list of Push namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    push_tuples = []
    for path in master_repo_paths:
        repo_base_name = os.path.basename(path)
        push_tuples += [
            git.Push(local_path=path, repo_url=repo_url, branch="master")
            for repo_url in repo_urls
            if repo_url.endswith(repo_base_name)
            or repo_url.endswith(repo_base_name + ".git")
        ]
    return push_tuples


def show_config() -> None:
    """Print the configuration file to the log."""
    config.check_config_integrity()

    LOGGER.info(
        "Found valid config file at " + str(constants.DEFAULT_CONFIG_FILE)
    )
    with constants.DEFAULT_CONFIG_FILE.open(
        encoding=sys.getdefaultencoding()
    ) as f:
        config_contents = "".join(f.readlines())

    output = (
        os.linesep
        + "BEGIN CONFIG FILE".center(50, "-")
        + os.linesep
        + config_contents
        + "END CONFIG FILE".center(50, "-")
    )

    LOGGER.info(output)
