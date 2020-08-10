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

import repobee_plug as plug

import _repobee.command.teams

from _repobee import git
from _repobee import util
from _repobee import exception
from _repobee import config
from _repobee import plugin
from _repobee.git import Push

from _repobee.command import progresswrappers


def setup_student_repos(
    master_repo_urls: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.PlatformAPI,
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
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    authed_urls = [api.insert_auth(url) for url in master_repo_urls]
    master_repo_names = [util.repo_name(url) for url in authed_urls]
    teams = list(teams)

    with tempfile.TemporaryDirectory() as tmpdir:
        plug.log.info("Cloning into master repos ...")
        master_repo_paths = _clone_all(authed_urls, cwd=tmpdir)
        hook_results = plugin.execute_setup_tasks(
            master_repo_names, api, cwd=pathlib.Path(tmpdir)
        )

        created_teams = list(
            plug.cli.io.progress_bar(
                _repobee.command.teams.create_teams(
                    teams, plug.TeamPermission.PUSH, api
                ),
                total=len(teams),
                desc="Creating student teams",
            )
        )

        push_tuple_iter = _create_push_tuples(
            created_teams, authed_urls, master_repo_paths, api
        )
        push_tuple_iter_progress = plug.cli.io.progress_bar(
            push_tuple_iter,
            desc="Setting up student repos",
            total=len(teams) * len(authed_urls),
        )
        git.push(push_tuples=push_tuple_iter_progress)

    return hook_results


def _create_push_tuples(
    teams: Iterable[plug.Team],
    authed_master_urls: Iterable[str],
    master_repo_paths: Mapping[str, str],
    api: plug.PlatformAPI,
) -> Iterable[Push]:
    """
    Args:
        teams: An iterable of teams.
        authed_master_urls: An iterable of authenticated master repo urls.
        master_repo_paths: A mapping (master_repo_url -> master_repo_path).
        api: A platform API instance.
    Returns:
        A list of Push namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    for team, authed_master_url in itertools.product(
        teams, authed_master_urls
    ):
        master_repo_name = api.extract_repo_name(authed_master_url)
        repo_name = plug.generate_repo_name(team, master_repo_name)
        repo = _create_or_fetch_repo(
            plug.generate_repo_name(team, master_repo_name),
            description=f"{repo_name} created for {team.name}",
            private=True,
            team=team,
            api=api,
        )
        local_path = master_repo_paths[authed_master_url]

        yield git.Push(
            local_path=local_path,
            repo_url=api.insert_auth(repo.url),
            branch="master",
        )


def _create_or_fetch_repo(
    name: str,
    description: str,
    private: bool,
    team: plug.Team,
    api: plug.PlatformAPI,
) -> plug.Repo:
    try:
        return api.create_repo(
            name, description=description, private=private, team=team,
        )
    except plug.PlatformError:
        repo = api.get_repo(repo_name=name, team_name=team.name)
        api.assign_repo(
            team=team, repo=repo, permission=plug.TeamPermission.PUSH
        )
        return repo


def _log_repo_creation(
    repos: Iterable[plug.Repo], total: int
) -> Iterable[plug.Repo]:
    for repo in plug.cli.io.progress_bar(
        repos,
        desc="Setting up student repositories",
        total=total,
        unit="repos",
    ):
        plug.log.info(f"Created repository {repo.name}")
        yield repo


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
        for url in plug.cli.io.progress_bar(
            urls, desc="Cloning template repositories", unit="repos"
        ):
            plug.log.info(f"Cloning into '{url}'")
            git.clone_single(url, cwd=cwd)
    except exception.CloneFailedError:
        plug.log.error("Error cloning into {}, aborting ...".format(url))
        raise
    paths = {url: os.path.join(cwd, util.repo_name(url)) for url in urls}
    return paths


def update_student_repos(
    master_repo_urls: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.PlatformAPI,
    issue: Optional[plug.Issue] = None,
) -> Mapping[str, List[plug.Result]]:
    """Attempt to update all student repos related to one of the master repos.

    Args:
        master_repo_urls: URLs to master repos. Must be in the organization
            that the api is set up for.
        teams: An iterable of student teams.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
        issue: An optional issue to open in repos to which pushing fails.
    """
    authed_template_urls = [api.insert_auth(url) for url in master_repo_urls]

    if len(set(authed_template_urls)) != len(authed_template_urls):
        raise ValueError("master_repo_urls contains duplicates")

    master_repo_names = [util.repo_name(url) for url in authed_template_urls]

    with tempfile.TemporaryDirectory() as tmpdir:
        plug.log.info("Cloning into master repos ...")
        master_repo_paths = _clone_all(authed_template_urls, tmpdir)
        hook_results = plugin.execute_setup_tasks(
            master_repo_names, api, cwd=pathlib.Path(tmpdir)
        )

        # we want to exhaust this iterator immediately to not have progress
        # bars overlap
        fetched_teams = list(progresswrappers.get_teams(teams, api))

        push_tuple_iter = _create_push_tuples(
            fetched_teams, authed_template_urls, master_repo_paths, api
        )

        push_tuple_iter_progress = plug.cli.io.progress_bar(
            push_tuple_iter,
            desc="Setting up student repos",
            total=len(teams) * len(authed_template_urls),
        )
        failed_urls = git.push(push_tuples=push_tuple_iter_progress)

    if failed_urls and issue:
        plug.echo("Opening issue in repos to which push failed")
        _open_issue_by_urls(failed_urls, issue, api)

    plug.log.info("Done!")
    return hook_results


def _open_issue_by_urls(
    repo_urls: Iterable[str], issue: plug.Issue, api: plug.PlatformAPI
) -> None:
    """Open issues in the repos designated by the repo_urls.

    Args:
        repo_urls: URLs to repos in which to open an issue.
        issue: An issue to open.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_names = [util.repo_name(url) for url in repo_urls]
    repos = progresswrappers.get_repos(repo_names, api)
    for repo in repos:
        issue = api.create_issue(issue.title, issue.body, repo)
        msg = f"Opened issue {repo.name}/#{issue.number}-'{issue.title}'"
        repos.write(msg)
        plug.log.info(msg)


def clone_repos(
    repos: Iterable[plug.Repo], api: plug.PlatformAPI
) -> Mapping[str, List[plug.Result]]:
    """Clone all student repos related to the provided master repos and student
    teams.

    Args:
        repos: The repos to be cloned. This function does not use the
            ``implementation`` attribute, so it does not need to be set.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    Returns:
        A mapping from repo name to a list of hook results.
    """
    repos_for_tasks, repos_for_clone = itertools.tee(repos)
    non_local_repos = _non_local_repos(repos_for_clone)

    plug.echo("Cloning into student repos ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        _clone_repos_no_check(non_local_repos, tmpdir, api)

    for p in plug.manager.get_plugins():
        if "post_clone" in dir(p):
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
            plug.log.warning("{} already on disk, skipping".format(repo.name))


def _clone_repos_no_check(repos, dst_dirpath, api) -> List[str]:
    """Clone the specified repo urls into the destination directory without
    making any sanity checks; they must be done in advance.

    Return a list of names of the successfully cloned repos.
    """
    repos_iter_a, repos_iter_b = itertools.tee(repos)
    repo_urls = (api.insert_auth(repo.url) for repo in repos_iter_b)

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


def migrate_repos(
    master_repo_urls: Iterable[str], api: plug.PlatformAPI
) -> None:
    """Migrate a repository from an arbitrary URL to the target organization.
    The new repository is added to the master_repos team, which is created if
    it does not already exist.

    Args:
        master_repo_urls: HTTPS URLs to the master repos to migrate.
            the username that is used in the push.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    master_names = [util.repo_name(url) for url in master_repo_urls]

    repos = [
        api.create_repo(name=template_name, description="", private=True)
        for template_name in master_names
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        _clone_all(master_repo_urls, cwd=tmpdir)

        git.push(
            [
                git.Push(
                    local_path=os.path.join(tmpdir, repo.name),
                    repo_url=api.insert_auth(repo.url),
                    branch="master",
                )
                for repo in repos
            ]
        )

    plug.echo("Done!")


def show_config(config_file: pathlib.Path) -> None:
    """Print the configuration file to the log."""
    config.check_config_integrity(config_file)

    plug.echo(f"Found valid config file at {config_file}")
    with config_file.open(encoding=sys.getdefaultencoding()) as f:
        config_contents = "".join(f.readlines())

    output = (
        os.linesep
        + "BEGIN CONFIG FILE".center(50, "-")
        + os.linesep
        + config_contents
        + "END CONFIG FILE".center(50, "-")
    )

    plug.echo(output)
