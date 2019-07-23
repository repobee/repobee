"""Primary API for _repobee.

This module contains high level functions for administrating repositories, such
as creating student repos from some master repo template. All functions follow
the conventions specified in :ref:`conventions`.

Each public function in this module is to be treated as a self-contained
program.

.. module:: command
    :synopsis: The primary API of repobee containing high level functions for
        administrating GitHub repos in an opinionated fashion.

.. moduleauthor:: Simon Larsén
"""
import pathlib
import shutil
import os
import sys
import tempfile
from typing import Iterable, List, Optional, Tuple, Generator
from colored import bg, fg, style

import daiquiri

import repobee_plug as plug

from _repobee import git
from _repobee import util
from _repobee import exception
from _repobee import config
from _repobee import constants
from _repobee import formatters
from _repobee.git import Push

LOGGER = daiquiri.getLogger(__file__)


def setup_student_repos(
    master_repo_urls: Iterable[str], teams: Iterable[plug.Team], api: plug.API
) -> None:
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

    with tempfile.TemporaryDirectory() as tmpdir:
        LOGGER.info("Cloning into master repos ...")
        master_repo_paths = _clone_all(urls, cwd=tmpdir)

        teams = _add_students_to_teams(teams, api)
        repo_urls = _create_student_repos(urls, teams, api)

        push_tuples = _create_push_tuples(master_repo_paths, repo_urls)
        LOGGER.info("Pushing files to student repos ...")
        git.push(push_tuples)


def _add_students_to_teams(
    teams: Iterable[plug.Team], api: plug.API
) -> List[plug.Team]:
    """Create the specified teams on the target platform,
    and add the specified members to their teams. If a team already exists, it
    is not created. If a student is already in his/her team, that student is
    ignored.

    Args:
        teams: Team objects specifying student groups.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    Returns:
        all teams associated with the students in the students list.
    """
    return api.ensure_teams_and_members(teams)


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
) -> None:
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

        push_tuples = _create_push_tuples(master_repo_paths, repo_urls)

        LOGGER.info("Pushing files to student repos ...")
        failed_urls = git.push(push_tuples)

    if failed_urls and issue:
        LOGGER.info("Opening issue in repos to which push failed")
        _open_issue_by_urls(failed_urls, issue, api)

    LOGGER.info("Done!")


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


def list_issues(
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.API,
    state: str = "open",
    title_regex: str = "",
    show_body: bool = False,
    author: Optional[str] = None,
) -> None:
    """List all issues in the specified repos.

    Args:
        master_repo_names: Names of master repositories.
        teams: An iterable of student teams.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
        state: state of the repo (open or closed). Defaults to 'open'.
        title_regex: If specified, only issues with titles matching the regex
            are displayed. Defaults to the empty string (which matches
            everything).
        show_body: If True, the body of the issue is displayed along with the
            default info.
        author: Only show issues by this author.
    """
    repo_names = util.generate_repo_names(teams, master_repo_names)
    max_repo_name_length = max(map(len, repo_names))

    issues_per_repo = api.get_issues(repo_names, state, title_regex)

    if author:
        issues_per_repo = (
            (repo_name, (issue for issue in issues if issue.author == author))
            for repo_name, issues in issues_per_repo
        )

    _log_repo_issues(issues_per_repo, show_body, max_repo_name_length + 6)


def _log_repo_issues(
    issues_per_repo: Tuple[str, Generator[plug.Issue, None, None]],
    show_body: bool,
    title_alignment: int,
) -> None:
    """Log repo issues.

    Args:
        issues_per_repo: (repo_name, issue generator) pairs
        show_body: Include the body of the issue in the output.
        title_alignment: Where the issue title should start counting from the
            start of the line.
    """
    even = True
    for repo_name, issues in issues_per_repo:
        issues = list(issues)

        if not issues:
            LOGGER.warning("{}: No matching issues".format(repo_name))

        for issue in issues:
            color = (bg("grey_30") if even else bg("grey_15")) + fg("white")
            even = not even  # cycle color
            adjusted_alignment = title_alignment + len(
                color
            )  # color takes character space

            id_ = "{}{}/#{}:".format(color, repo_name, issue.number).ljust(
                adjusted_alignment
            )
            out = "{}{}{}{}created {!s} by {}".format(
                id_,
                issue.title,
                style.RESET,
                " ",
                issue.created_at,
                issue.author,
            )
            if show_body:
                out += os.linesep * 2 + _limit_line_length(issue.body)
            LOGGER.info(out)


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


def open_issue(
    issue: plug.Issue,
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.API,
) -> None:
    """Open an issue in student repos.

    Args:
        master_repo_names: Names of master repositories.
        teams: Team objects specifying student groups.
        issue: An issue to open.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_names = util.generate_repo_names(teams, master_repo_names)
    api.open_issue(issue.title, issue.body, repo_names)


def close_issue(
    title_regex: str,
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Team],
    api: plug.API,
) -> None:
    """Close issues whose titles match the title_regex in student repos.

    Args:
        title_regex: A regex to match against issue titles.
        master_repo_names: Names of master repositories.
        teams: Team objects specifying student groups.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_names = util.generate_repo_names(teams, master_repo_names)
    api.close_issue(title_regex, repo_names)


def clone_repos(
    master_repo_names: Iterable[str], teams: Iterable[plug.Team], api: plug.API
) -> None:
    """Clone all student repos related to the provided master repos and student
    teams.

    Args:
        master_repo_names: Names of master repos.
        teams: An iterable of student teams.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    repo_urls = api.get_repo_urls(master_repo_names, teams=teams)
    # the reason we first compute the urls and then extract repo names is that
    # GitLab needs the team names for namespacing: you can't reliably go from
    # student repo name to student repo url!
    repo_names = list(map(api.extract_repo_name, repo_urls))
    name_conflicts = util.conflicting_files(map(str, repo_names), cwd=".")
    clone_urls = [
        url
        for url in repo_urls
        if api.extract_repo_name(url) not in name_conflicts
    ]
    for repo_name in name_conflicts:
        LOGGER.warning("{} already exists, skipping".format(repo_name))

    LOGGER.info("Cloning into student repos ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        _clone_repos_no_check(clone_urls, tmpdir, api)

    for plugin in plug.manager.get_plugins():
        if "act_on_cloned_repo" in dir(plugin):
            repo_names = util.generate_repo_names(teams, master_repo_names)
            _execute_post_clone_hooks(repo_names, api)
            break


def _clone_repos_no_check(repo_urls, dst_dirpath, api):
    """Clone the specified repo urls into the destination directory without
    making any sanity checks; they must be done in advance.

    Return a list of names of the successfully cloned repos.
    """
    fail_urls = git.clone(repo_urls, cwd=dst_dirpath)
    fail_repo_names = set(api.extract_repo_name(url) for url in fail_urls)
    cloned_repos = [
        path
        for path in pathlib.Path(dst_dirpath).iterdir()
        if path.is_dir()
        and util.is_git_repo(str(path))
        and path.name not in fail_repo_names
    ]

    cur_dir = pathlib.Path(".").resolve()
    for repo in cloned_repos:
        shutil.copytree(src=str(repo), dst=str(cur_dir / repo.name))
    return [repo.name for repo in cloned_repos]


def _execute_post_clone_hooks(repo_names: List[str], api: plug.API):
    LOGGER.info("Executing post clone hooks on repos")
    local_repos = [name for name in os.listdir() if name in repo_names]

    results = {}
    for repo_name in local_repos:
        LOGGER.info("Executing post clone hooks on {}".format(repo_name))
        res = plug.manager.hook.act_on_cloned_repo(
            path=os.path.abspath(repo_name), api=api
        )
        results[repo_name] = res
    LOGGER.info(formatters.format_hook_results_output(results))

    LOGGER.info("Post clone hooks done")


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


def assign_peer_reviews(
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Status],
    num_reviews: int,
    issue: Optional[plug.Issue],
    api: plug.API,
) -> None:
    """Assign peer reviewers among the students to each student repo. Each
    student is assigned to review num_reviews repos, and consequently, each
    repo gets reviewed by num_reviews reviewers.

    In practice, each student repo has a review team generated (called
    <student-repo-name>-review), to which num_reviews _other_ students are
    assigned. The team itself is given pull-access to the student repo, so
    that reviewers can view code and open issues, but cannot modify the
    contents of the repo.

    Args:
        master_repo_names: Names of master repos.
        teams: Team objects specifying student groups.
        num_reviews: Amount of reviews each student should perform
            (consequently, the amount of reviews of each repo)
        issue: An issue with review instructions to be opened in the considered
            repos.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    for master_name in master_repo_names:
        allocations = plug.manager.hook.generate_review_allocations(
            teams=teams, num_reviews=num_reviews
        )
        # adjust names of review teams
        review_teams, reviewed_teams = list(
            zip(
                *[
                    (
                        plug.Team(
                            members=alloc.review_team.members,
                            name=util.generate_review_team_name(
                                str(alloc.reviewed_team), master_name
                            ),
                        ),
                        alloc.reviewed_team,
                    )
                    for alloc in allocations
                ]
            )
        )
        api.ensure_teams_and_members(
            review_teams, permission=plug.TeamPermission.PULL
        )
        api.add_repos_to_review_teams(
            {
                review_team.name: [
                    util.generate_repo_name(reviewed_team, master_name)
                ]
                for review_team, reviewed_team in zip(
                    review_teams, reviewed_teams
                )
            },
            issue=issue,
        )


def purge_review_teams(
    master_repo_names: Iterable[str],
    students: Iterable[plug.Team],
    api: plug.API,
) -> None:
    """Delete all review teams associated with the given master repo names and
    students.

    Args:
        master_repo_names: Names of master repos.
        students: An iterble of student teams.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    review_team_names = [
        util.generate_review_team_name(student, master_repo_name)
        for student in students
        for master_repo_name in master_repo_names
    ]
    api.delete_teams(review_team_names)


def check_peer_review_progress(
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Team],
    title_regex: str,
    num_reviews: int,
    api: plug.API,
) -> None:
    """Check which teams have opened peer review issues in their allotted
    review repos

    Args:
        master_repo_names: Names of master repos.
        teams: An iterable of student teams.
        title_regex: A regex to match against issue titles.
        num_reviews: Amount of reviews each student is expected to have made.
        api: An implementation of :py:class:`repobee_plug.API` used to
            interface with the platform (e.g. GitHub or GitLab) instance.

    """
    review_team_names = [
        util.generate_review_team_name(team, master_name)
        for team in teams
        for master_name in master_repo_names
    ]
    reviews = api.get_review_progress(review_team_names, teams, title_regex)

    LOGGER.info(
        formatters.format_peer_review_progress_output(
            reviews, teams, num_reviews
        )
    )


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
                name=util.generate_repo_name(team.name, repo_base_name),
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
