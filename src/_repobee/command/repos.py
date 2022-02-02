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
from typing import Iterable, List, Optional, Mapping, Union, Tuple, Any

import repobee_plug as plug

import _repobee.command.teams
import _repobee.config

from _repobee import exception, git, plugin, urlutil
from _repobee.fileutil import DirectoryLayout
from _repobee.git import PushSpec
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
                name=urlutil.extract_repo_name(url),
                url=url,
                _path=workdir / api.extract_repo_name(url),
            )
            for url in template_repo_urls
        ]

        plug.log.info("Cloning into master repos ...")
        _clone_all(template_repos, cwd=workdir, api=api)
        pre_setup_results = plugin.execute_setup_tasks(
            template_repos, api, cwd=pathlib.Path(tmpdir)
        )

        platform_teams = _create_platform_teams(teams, api)

        to_push, preexisting = _create_state_separated_push_tuples(
            platform_teams, template_repos, api
        )
        successful_pts, _ = git.push(push_tuples=to_push)

        post_setup_results = _execute_post_setup_hook(
            successful_pts, preexisting, api
        )

    return _combine_dicts(pre_setup_results, post_setup_results)


def _combine_dicts(*dicts):
    base = dict(dicts[0])
    others = dicts[1:]

    for key, value in itertools.chain.from_iterable(
        [d.items() for d in others]
    ):
        if key in base:
            base[key].extend(value)
        else:
            base[key] = value

    return base


def _create_platform_teams(
    teams: List[plug.StudentTeam], api: plug.PlatformAPI
) -> List[plug.Team]:
    return list(
        plug.cli.io.progress_bar(
            _repobee.command.teams.create_teams(
                teams, plug.TeamPermission.PUSH, api
            ),
            total=len(teams),
            desc="Creating student teams",
        )
    )


def _execute_post_setup_hook(
    pushed: List[PushSpec], preexisting: List[PushSpec], api: plug.PlatformAPI
) -> Mapping[Any, Any]:
    """Execute the post_setup hook on the given push tuples. Note that the push
    tuples are expected to have the "team" and "repo" keys set in the metadata.
    """
    post_setup_exists = any(
        ["post_setup" in dir(p) for p in plug.manager.get_plugins()]
    )
    if not post_setup_exists or not pushed and not preexisting:
        return {}

    pushed_results = _post_setup(pushed, newly_created=True, api=api)
    preexisting_results = _post_setup(
        preexisting, newly_created=False, api=api
    )

    return _combine_dicts(pushed_results, preexisting_results)


def _post_setup(
    pts: List[PushSpec], newly_created: bool, api: plug.PlatformAPI
) -> Mapping[Any, Any]:
    teams_and_repos = [
        (pt.metadata["team"], pt.metadata["repo"]) for pt in pts
    ]
    student_repos = [
        plug.StudentRepo(
            name=repo.name,
            url=repo.url,
            team=plug.StudentTeam(name=team.name, members=team.members),
        )
        for team, repo in teams_and_repos
    ]
    student_repos_iter = plug.cli.io.progress_bar(
        student_repos, desc="Executing post_setup hooks"
    )

    return plugin.execute_tasks(
        student_repos_iter,
        plug.manager.hook.post_setup,
        api,
        cwd=None,
        copy_repos=False,
        extra_kwargs=dict(newly_created=newly_created),
    )


def _create_state_separated_push_tuples(
    teams: List[plug.Team],
    template_repos: List[plug.TemplateRepo],
    api: plug.PlatformAPI,
) -> Tuple[List[PushSpec], List[PushSpec]]:
    """Return a tuple of lists of template repos, where the first list contains
    push tuples for newly created repos and the second list contains push
    tuples for repos that already existed.
    """
    push_tuple_iter = _create_push_tuples(teams, template_repos, api)
    push_tuple_iter_progress = plug.cli.io.progress_bar(
        push_tuple_iter,
        desc="Setting up student repos",
        total=len(teams) * len(template_repos),
    )

    newly_created = []
    preexisting = []
    for created, pt in push_tuple_iter_progress:
        if created:
            newly_created.append(pt)
        else:
            preexisting.append(pt)

    return newly_created, preexisting


def _create_push_tuples(
    teams: List[plug.Team],
    template_repos: Iterable[plug.TemplateRepo],
    api: plug.PlatformAPI,
) -> Iterable[Tuple[bool, PushSpec]]:
    """Create push tuples for newly created repos. Repos that already exist are
    ignored.

    Args:
        teams: An iterable of teams.
        template_repos: Template repositories.
        api: A platform API instance.
    Returns:
        A list of tuples (created, push_tuple) for all student repo urls
        that relate to any of the master repo urls. ``created`` indicates
        whether or not the student repo was created in this invocation.
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

        yield created, PushSpec(
            local_path=template_repo.path,
            repo_url=api.insert_auth(repo.url),
            branch=git.active_branch(template_repo.path),
            metadata=dict(repo=repo, team=team),
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
    repos: Iterable[plug.TemplateRepo],
    cwd: pathlib.Path,
    api: plug.PlatformAPI,
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
    template_repo_urls: plug.types.SizedIterable[str],
    teams: plug.types.SizedIterable[plug.StudentTeam],
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
                name=urlutil.extract_repo_name(url),
                url=url,
                _path=workdir / api.extract_repo_name(url),
            )
            for url in template_repo_urls
        ]

        plug.log.info("Cloning into master repos ...")
        _clone_all(template_repos, cwd=workdir, api=api)
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
        successful_pts, failed_pts = git.push(
            push_tuples=push_tuple_iter_progress
        )

    if failed_pts and issue:
        plug.echo("Opening issue in repos to which push failed")
        urls_without_auth = [
            re.sub("https://.*?@", "https://", pt.repo_url)
            for pt in failed_pts
        ]
        _open_issue_by_urls(urls_without_auth, issue, api)

    plug.log.info("Done!")
    return hook_results


def _create_update_push_tuples(
    teams: Iterable[plug.StudentTeam],
    template_repos: Iterable[plug.TemplateRepo],
    api: plug.PlatformAPI,
) -> Iterable[PushSpec]:
    """Create push tuples for existing repos. Repos that don't exist are
    ignored.

    Args:
        teams: An iterable of teams.
        template_repos: Template repositories.
        api: A platform API instance.
    Returns:
        A list of PushSpec namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    urls_to_templates = {}
    for team, template_repo in itertools.product(teams, template_repos):
        repo_url, *_ = api.get_repo_urls(
            [template_repo.name], team_names=[team.name]
        )
        urls_to_templates[repo_url] = template_repo

    for repo in api.get_repos(list(urls_to_templates.keys())):
        template = urls_to_templates[repo.url]
        branch = git.active_branch(template.path)
        yield PushSpec(template.path, api.insert_auth(repo.url), branch)


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
        repos.write(msg)  # type: ignore
        plug.log.info(msg)


def clone_repos(
    repos: Iterable[plug.StudentRepo],
    update_local: bool,
    directory_layout: DirectoryLayout,
    api: plug.PlatformAPI,
) -> Mapping[str, List[plug.Result]]:
    """Clone all student repos related to the provided master repos and student
    teams.

    Args:
        repos: The repos to be cloned. This function does not use the
            ``implementation`` attribute, so it does not need to be set.
        update_local: Whether or nut to attempt to update student repos
            that already exist locally.
        directory_layout: The layout to use for organizing cloned
            repositories.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    Returns:
        A mapping from repo name to a list of hook results.
    """

    plug.echo("Cloning into student repos ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        pathed_repos = _with_output_paths(repos, directory_layout)
        local_repos = _clone_repos(
            pathed_repos, pathlib.Path(tmpdir), update_local, api
        )
        _set_pull_ff_only(local_repos)

    for p in plug.manager.get_plugins():
        if "post_clone" in dir(p):
            local_repos_progress = plug.cli.io.progress_bar(
                local_repos, desc="Executing post_clone hooks"
            )
            return plugin.execute_clone_tasks(local_repos_progress, api)
    return {}


def _set_pull_ff_only(local_repos: List[plug.StudentRepo]) -> None:
    for repo in local_repos:
        git.set_gitconfig_options(repo.path, {"pull.ff": "only"})


def _with_output_paths(
    repos: Iterable[plug.StudentRepo],
    directory_layout: DirectoryLayout,
) -> List[plug.StudentRepo]:
    base_dir = pathlib.Path(".").resolve()
    return [
        repo.with_path(directory_layout.get_repo_path(base_dir, repo))
        for repo in repos
    ]


def _clone_repos(
    pathed_repos: List[plug.StudentRepo],
    dst_dirpath: pathlib.Path,
    update_local: bool,
    api: plug.PlatformAPI,
) -> List[plug.StudentRepo]:
    """Clone the specified repo urls into the destination directory."""
    _check_for_non_git_dir_path_clashes(pathed_repos)

    cloned_repos = git.clone_student_repos(
        pathed_repos, dst_dirpath, update_local, api
    )

    non_updated_local = (
        git.CloneStatus.EXISTED in [stat for stat, _ in cloned_repos]
        and not update_local
    )
    if non_updated_local:
        plug.log.warning(
            "Local repos were not updated, use `--update-local` to update"
        )

    return [
        repo
        for status, repo in cloned_repos
        if status != git.CloneStatus.FAILED
    ]


def _check_for_non_git_dir_path_clashes(repos: List[plug.StudentRepo]) -> None:
    """Raise if any of the student repo paths clash with a non-git
    directory.
    """
    for repo in repos:
        if repo.path.exists() and not git.is_git_repo(repo.path):
            raise exception.RepoBeeException(
                f"name clash with directory that is not a Git repository: "
                f"'{repo.path}'"
            )


def migrate_repos(
    template_repo_urls: plug.types.SizedIterable[str], api: plug.PlatformAPI
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
        plug.TemplateRepo(name=urlutil.extract_repo_name(url), url=url)
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
                PushSpec(
                    local_path=template_repo.path,
                    repo_url=api.insert_auth(template_repo.url),
                    branch=git.active_branch(template_repo.path),
                )
                for template_repo in remote_templates
            ]
        )

    plug.echo("Done!")


def show_config(config: plug.Config, show_secrets: bool) -> None:
    """Echo the config file.

    Args:
        config: The config to show.
        show_secrets: Whether or not to show configured secrets.
    """
    _repobee.config.check_config_integrity(config.path)

    plug.echo(f"Found valid config file at {config.path}")
    with config.path.open(encoding=sys.getdefaultencoding()) as f:
        config_contents = "".join(f.readlines())

    output = (
        os.linesep
        + "BEGIN CONFIG FILE".center(50, "-")
        + os.linesep
        + config_contents
        + "END CONFIG FILE".center(50, "-")
    )
    sanitized_output = re.sub(r"token\s*=\s*.*", "token = xxxxxxxxxx", output)

    plug.echo(output if show_secrets else sanitized_output)
