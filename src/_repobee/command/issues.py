"""Top-level commands for managing issues.

This module contains the top-level functions for RepoBee's issue management
functionality. Each public function in this module is to be treated as a
self-contained program.

.. module:: issues
    :synopsis: Top-level commands for issue management.

.. moduleauthor:: Simon Larsén
"""
import os
import re
import dataclasses
from typing import Iterable, Optional, List, Tuple, Any, Mapping

import repobee_plug as plug

import _repobee.hash
from _repobee.command import progresswrappers
from _repobee.colors import BackgroundColor, ForegroundColor, RESET


def _hash_if_key(s: str, key: Optional[str], max_hash_size: int = 20) -> str:
    """Hash the string with the key, if provided. Otherwise, return the input
    string.
    """
    return _repobee.hash.keyed_hash(s, key, max_hash_size) if key else s


def list_issues(
    repos: Iterable[plug.StudentRepo],
    api: plug.PlatformAPI,
    state: plug.IssueState = plug.IssueState.OPEN,
    title_regex: str = "",
    show_body: bool = False,
    author: Optional[str] = None,
    double_blind_key: Optional[str] = None,
) -> Mapping[str, List[plug.Result]]:
    """List all issues in the specified repos.

    Args:
        repos: The repos from which to fetch issues.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
        state: state of the repo (open or closed). Defaults to open.
        title_regex: If specified, only issues with titles matching the regex
            are displayed. Defaults to the empty string (which matches
            everything).
        show_body: If True, the body of the issue is displayed along with the
            default info.
        author: Only show issues by this author.
        double_blind_key: If provided, use to deanonymize anonymous repos.
    """
    # TODO optimize by not getting all repos at once
    repos = list(repos)
    repo_names = [repo.name for repo in repos]
    max_repo_name_length = max(map(len, repo_names))

    issues_per_repo = _get_issue_generator(
        repos,
        title_regex=title_regex,
        author=author,
        state=state,
        double_blind_key=double_blind_key,
        api=api,
    )

    # _log_repo_issues exhausts the issues_per_repo iterator and
    # returns a list with the same information. It's important to
    # have issues_per_repo as an iterator as it greatly speeds
    # up visual feedback to the user when fetching many issues
    pers_issues_per_repo = _log_repo_issues(
        issues_per_repo, show_body, max_repo_name_length + 6
    )

    # for writing to JSON
    hook_result_mapping = {
        repo.name: [
            plug.Result(
                name="list-issues",
                status=plug.Status.SUCCESS,
                msg=f"Fetched {len(issues)} issues from {repo.name}",
                data={issue.number: issue.to_dict() for issue in issues},
            )
        ]
        for repo, issues in pers_issues_per_repo
    }

    # meta hook result
    hook_result_mapping["list-issues"] = [
        plug.Result(
            name="meta",
            status=plug.Status.SUCCESS,
            msg="Meta info about the list-issues hook results",
            data={"state": state.value},
        )
    ]

    # new experimental format for repo data used by `issues list` with
    # --hook-results-file
    repos_data = {repo.url: dataclasses.asdict(repo) for repo in repos}
    for repo, issues in pers_issues_per_repo:
        repos_data[repo.url]["issues"] = {
            issue.number: issue.to_dict() for issue in issues
        }
    hook_result_mapping["repos"] = [
        plug.Result("repos", plug.Status.SUCCESS, "repo_data", data=repos_data)
    ]

    return hook_result_mapping


def _get_issue_generator(
    repos: Iterable[plug.StudentRepo],
    title_regex: str,
    author: Optional[str],
    state: plug.IssueState,
    double_blind_key: Optional[str],
    api: plug.PlatformAPI,
) -> Iterable[Tuple[plug.StudentRepo, Iterable[plug.Issue]]]:
    for repo in repos:
        if double_blind_key:
            team_name = _hash_if_key(repo.team.name, double_blind_key)
            repo_name = _hash_if_key(repo.name, double_blind_key)
            platform_repo = api.get_repo(repo_name, team_name)
        else:
            platform_repo = api.get_repo(repo.name, repo.team.name)

        yield repo, [
            issue
            for issue in api.get_repo_issues(platform_repo)
            if re.match(title_regex, issue.title)
            and (state in [plug.IssueState.ALL, issue.state])
            and (not author or issue.author == author)
        ]


def _log_repo_issues(
    issues_per_repo: Iterable[Tuple[plug.StudentRepo, Iterable[plug.Issue]]],
    show_body: bool,
    title_alignment: int,
) -> List[Tuple[Any, list]]:
    """Log repo issues.

    Args:
        issues_per_repo: (repo, issue generator) pairs
        show_body: Include the body of the issue in the output.
        title_alignment: Where the issue title should start counting from the
            start of the line.
    """
    even = True
    persistent_issues_per_repo = []
    for repo, issues in issues_per_repo:
        issues = list(issues)
        persistent_issues_per_repo.append((repo, issues))

        if not issues:
            plug.log.warning(f"{repo.name}: No matching issues")

        for issue in issues:
            bg_color = (
                BackgroundColor.LIGHT_GREY
                if even
                else BackgroundColor.DARK_GREY
            )
            color = f"{bg_color}{ForegroundColor.WHITE}"

            even = not even  # cycle color
            adjusted_alignment = title_alignment + len(
                color
            )  # color takes character space

            id_ = f"{color}{repo.name}/#{issue.number}:".ljust(
                adjusted_alignment
            )
            out = f"{id_}{issue.title}{RESET} created {issue.created_at} by {issue.author}"
            if show_body:
                out += os.linesep * 2 + _limit_line_length(issue.body)
            plug.echo(out)

    return persistent_issues_per_repo


def _limit_line_length(s: str, max_line_length: int = 100) -> str:
    """Return the input string with lines no longer than max_line_length.

    Args:
        s: Any string.
        max_line_length: Maximum allowed line length.
    Returns:
        the input string with lines no longer than max_line_length.
    """
    lines = s.split(os.linesep)
    out = ""
    for line in lines:
        cur = 0
        while len(line) - cur > max_line_length:
            # find ws closest to the line length
            idx = line.rfind(" ", cur, max_line_length + cur)
            idx = max_line_length + cur if idx <= 0 else idx
            if line[idx] == " ":
                out += line[cur:idx]
            else:
                out += line[cur : idx + 1]
            out += os.linesep
            cur = idx + 1
        out += line[cur : cur + max_line_length] + os.linesep
    return out


def open_issues_from_hook_results(
    hook_results: Mapping[str, List[plug.Result]],
    repos: Iterable[plug.StudentRepo],
    api: plug.PlatformAPI,
) -> None:
    """Open all issues from the hook results in the given repos. Issues given
    in the hook results that do not belong to the repos are ignored, and repos
    provided without corresponding issues in the hook results have no effect.

    Args:
        hook_results: A hook results dictionary.
        repos: Student repos to open issues in.
        api: plug.PlatformAPI,
    """
    url_to_repo = {repo.url: repo for repo in repos}
    for repo_url, repo_data in hook_results["repos"][0].data.items():
        if repo_url in url_to_repo and repo_data["issues"]:
            repo = url_to_repo[repo_url]
            platform_repo = api.get_repo(repo.name, repo.team.name)

            for issue_data in repo_data["issues"].values():
                issue = api.create_issue(
                    issue_data["title"], issue_data["body"], platform_repo
                )
                msg = (
                    f"Opened issue {repo.name}/#{issue.number}-'{issue.title}'"
                )
                plug.echo(msg)


def open_issue(
    issue: plug.Issue,
    assignment_names: Iterable[str],
    teams: Iterable[plug.StudentTeam],
    api: plug.PlatformAPI,
) -> None:
    """Open an issue in student repos.

    Args:
        assignment_names: Names of assignments.
        teams: Team objects specifying student groups.
        issue: An issue to open.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_urls = api.get_repo_urls(
        team_names=[t.name for t in teams], assignment_names=assignment_names
    )
    repos = progresswrappers.get_repos(repo_urls, api)
    for repo in repos:
        issue = api.create_issue(issue.title, issue.body, repo)
        msg = f"Opened issue {repo.name}/#{issue.number}-'{issue.title}'"
        repos.write(msg)  # type: ignore
        plug.log.info(msg)


def close_issue(
    title_regex: str, repos: Iterable[plug.StudentRepo], api: plug.PlatformAPI
) -> None:
    """Close issues whose titles match the title_regex in student repos.

    Args:
        title_regex: A regex to match against issue titles.
        assignment_names: Names of assignments.
        teams: Team objects specifying student groups.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_urls = (repo.url for repo in repos)
    platform_repos = progresswrappers.get_repos(repo_urls, api)
    for repo in platform_repos:
        to_close = [
            issue
            for issue in api.get_repo_issues(repo)
            if re.match(title_regex, issue.title)
            and issue.state == plug.IssueState.OPEN
        ]
        for issue in to_close:
            api.close_issue(issue)
            msg = f"Closed {repo.name}/#{issue.number}='{issue.title}'"
            platform_repos.write(msg)  # type: ignore
            plug.log.info(msg)
