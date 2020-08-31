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
import re
import os
import sys
import tempfile
from typing import Iterable, List, Optional, Mapping, Union, Tuple

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
    template_repo_urls: Iterable[str],
    teams: Iterable[plug.StudentTeam],
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
        template_repo_urls: URLs to master repos.
        teams: An iterable of student teams specifying the teams to be setup.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    teams = list(teams)

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        template_repos = [
            plug.TemplateRepo(
                name=util.repo_name(url),
                url=url,
                _path=workdir / api.extract_repo_name(url),
            )
            for url in template_repo_urls
        ]

        plug.log.info("Cloning into master repos ...")
        _clone_all(template_repos, cwd=tmpdir, api=api)
        hook_results = plugin.execute_setup_tasks(
            template_repos, api, cwd=pathlib.Path(tmpdir)
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
            created_teams, template_repos, api
        )
        push_tuple_iter_progress = plug.cli.io.progress_bar(
            push_tuple_iter,
            desc="Setting up student repos",
            total=len(teams) * len(template_repos),
        )
        git.push(push_tuples=push_tuple_iter_progress)

    return hook_results


def _create_push_tuples(
    teams: Iterable[plug.Team],
    template_repos: Iterable[plug.TemplateRepo],
    api: plug.PlatformAPI,
) -> Iterable[Push]:
    """Create push tuples for newly created repos. Repos that already exist are
    ignored.

    Args:
        teams: An iterable of teams.
        template_repos: Template repositories.
        api: A platform API instance.
    Returns:
        A list of Push namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    for team, template_repo in itertools.product(teams, template_repos):
        repo_name = plug.generate_repo_name(team, template_repo.name)
        created, repo = _create_or_fetch_repo(
            name=repo_name,
            description=f"{repo_name} created for {team.name}",
            private=True,
            team=team,
            api=api,
        )

        if created:
            yield git.Push(
                local_path=template_repo.path,
                repo_url=api.insert_auth(repo.url),
                branch=git.active_branch(template_repo.path),
            )


def _create_or_fetch_repo(
    name: str,
    description: str,
    private: bool,
    api: plug.PlatformAPI,
    team: Optional[plug.Team] = None,
) -> Tuple[bool, plug.Repo]:
    try:
        return (
            True,
            api.create_repo(
                name, description=description, private=private, team=team
            ),
        )
    except plug.PlatformError:
        team_name = team.name if team else None
        repo = api.get_repo(repo_name=name, team_name=team_name)

        if team:
            api.assign_repo(
                team=team, repo=repo, permission=plug.TeamPermission.PUSH
            )
        return False, repo


def _clone_all(
    repos: plug.TemplateRepo, cwd: pathlib.Path, api: plug.PlatformAPI
):
    """Attempts to clone all repos sequentially.

    Args:
        repos: Repos to clone.
        cwd: Working directory. Use temporary directory for automatic cleanup.
        api: An instance of the platform API.
    """
    try:
        for repo in plug.cli.io.progress_bar(
            repos, desc="Cloning template repositories", unit="repos"
        ):
            url = _try_insert_auth(repo, api)
            plug.log.info(f"Cloning into '{url}'")
            git.clone_single(url, cwd=str(cwd))
    except exception.CloneFailedError:
        plug.log.error(f"Error cloning into {url}, aborting ...")
        raise


def _try_insert_auth(
    repo: Union[plug.TemplateRepo, plug.StudentRepo], api: plug.PlatformAPI
) -> str:
    """Try to insert authentication into the URL."""
    try:
        return api.insert_auth(repo.url)
    except plug.InvalidURL:
        return repo.url


def update_student_repos(
    template_repo_urls: Iterable[str],
    teams: Iterable[plug.StudentTeam],
    api: plug.PlatformAPI,
    issue: Optional[plug.Issue] = None,
) -> Mapping[str, List[plug.Result]]:
    """Attempt to update all student repos related to one of the master repos.

    Args:
        template_repo_urls: URLs to master repos. Must be in the organization
            that the api is set up for.
        teams: An iterable of student teams.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
        issue: An optional issue to open in repos to which pushing fails.
    """
    if len(set(template_repo_urls)) != len(template_repo_urls):
        raise ValueError("template_repo_urls contains duplicates")

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        template_repos = [
            plug.TemplateRepo(
                name=util.repo_name(url),
                url=url,
                _path=workdir / api.extract_repo_name(url),
            )
            for url in template_repo_urls
        ]

        plug.log.info("Cloning into master repos ...")
        _clone_all(template_repos, cwd=tmpdir, api=api)
        hook_results = plugin.execute_setup_tasks(
            template_repos, api, cwd=pathlib.Path(tmpdir)
        )

        push_tuple_iter = _create_update_push_tuples(
            teams, template_repos, api
        )
        push_tuple_iter_progress = plug.cli.io.progress_bar(
            push_tuple_iter,
            desc="Setting up student repos",
            total=len(teams) * len(template_repos),
        )
        failed_urls = git.push(push_tuples=push_tuple_iter_progress)

    if failed_urls and issue:
        plug.echo("Opening issue in repos to which push failed")
        urls_without_auth = [
            re.sub("https://.*?@", "https://", url) for url in failed_urls
        ]
        _open_issue_by_urls(urls_without_auth, issue, api)

    plug.log.info("Done!")
    return hook_results


def _create_update_push_tuples(
    teams: Iterable[plug.StudentTeam],
    template_repos: Iterable[plug.TemplateRepo],
    api: plug.PlatformAPI,
) -> Iterable[Push]:
    """Create push tuples for existing repos. Repos that don't exist are
    ignored.

    Args:
        teams: An iterable of teams.
        template_repos: Template repositories.
        api: A platform API instance.
    Returns:
        A list of Push namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    urls_to_templates = {}
    for team, template_repo in itertools.product(teams, template_repos):
        repo_url, *_ = api.get_repo_urls(
            [template_repo.name], team_names=[team.name]
        )
        urls_to_templates[repo_url] = template_repo

    for repo in api.get_repos(urls_to_templates.keys()):
        template = urls_to_templates[repo.url]
        branch = git.active_branch(template.path)
        yield git.Push(template.path, api.insert_auth(repo.url), branch)


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
    repos = progresswrappers.get_repos(repo_urls, api)
    for repo in repos:
        issue = api.create_issue(issue.title, issue.body, repo)
        msg = f"Opened issue {repo.name}/#{issue.number}-'{issue.title}'"
        repos.write(msg)
        plug.log.info(msg)


def clone_repos(
    repos: Iterable[plug.StudentRepo], api: plug.PlatformAPI
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

    plug.echo("Cloning into student repos ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        local_repos = _clone_repos_no_check(repos, pathlib.Path(tmpdir), api)

    for p in plug.manager.get_plugins():
        if "post_clone" in dir(p):
            local_repos_progress = plug.cli.io.progress_bar(
                local_repos, desc="Executing post_clone hooks"
            )
            return plugin.execute_clone_tasks(local_repos_progress, api)
    return {}


def _clone_repos_no_check(
    repos: Iterable[plug.StudentRepo],
    dst_dirpath: pathlib.Path,
    api: plug.PlatformAPI,
) -> Iterable[plug.StudentRepo]:
    """Clone the specified repo urls into the destination directory without
    making any sanity checks; they must be done in advance.

    Return a list of cloned and previously existing repos.
    """
    cur_dir = pathlib.Path(".").resolve()
    pathed_repos = [
        repo.with_path(cur_dir / repo.team.name / repo.name) for repo in repos
    ]

    cloned_repos = git.clone_student_repos(pathed_repos, dst_dirpath, api)
    return [repo for _, repo in cloned_repos]


def migrate_repos(
    template_repo_urls: Iterable[str], api: plug.PlatformAPI
) -> None:
    """Migrate a repository from an arbitrary URL to the target organization.
    The new repository is added to the master_repos team, which is created if
    it does not already exist.

    Args:
        template_repo_urls: Local urls to repos to migrate.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    local_templates = [
        plug.TemplateRepo(name=util.repo_name(url), url=url)
        for url in template_repo_urls
    ]
    create_repo_it = plug.cli.io.progress_bar(
        (
            _create_or_fetch_repo(
                local.name, description="", private=True, api=api
            )
            for local in local_templates
        ),
        desc="Creating remote repos",
        total=len(template_repo_urls),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        _clone_all(local_templates, cwd=workdir, api=api)

        remote_templates = [
            plug.TemplateRepo(
                name=repo.name, url=repo.url, _path=workdir / repo.name
            )
            for _, repo in create_repo_it
        ]

        git.push(
            [
                git.Push(
                    local_path=template_repo.path,
                    repo_url=api.insert_auth(template_repo.url),
                    branch=git.active_branch(template_repo.path),
                )
                for template_repo in remote_templates
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
