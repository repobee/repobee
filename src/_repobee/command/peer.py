"""Top-level commands for peer reviewing.

This module contains the top-level functions for RepoBee's peer review
functionality. Each public function in this module is to be treated as a
self-contained program.

.. module:: peer
    :synopsis: Top-level commands for peer reviewing.

.. moduleauthor:: Simon Larsén
"""
import itertools
import collections
import re
import tempfile
import pathlib
import shutil
from typing import Iterable, Optional, Dict, List, Tuple

import git  # type: ignore
import repobee_plug as plug

import _repobee.command.teams
import _repobee.git
import _repobee.ext.gitea
import _repobee.hash
from _repobee import formatters

from _repobee.command import progresswrappers

DEFAULT_REVIEW_ISSUE = plug.Issue(
    title="Peer review",
    body="You have been assigned to peer review this repo.",
)

_DEFAULT_BRANCH = "master"


def assign_peer_reviews(
    assignment_names: Iterable[str],
    teams: Iterable[plug.StudentTeam],
    num_reviews: int,
    issue: Optional[plug.Issue],
    double_blind_salt: Optional[str],
    api: plug.PlatformAPI,
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
        assignment_names: Names of assginments.
        teams: Team objects specifying student groups.
        num_reviews: Amount of reviews each student should perform
            (consequently, the amount of reviews of each repo)
        issue: An issue with review instructions to be opened in the considered
            repos.
        double_blind_salt: If provided, use salt to make double-blind review
            allocation.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    issue = issue or DEFAULT_REVIEW_ISSUE
    expected_repo_names = plug.generate_repo_names(teams, assignment_names)
    fetched_teams = progresswrappers.get_teams(
        teams, api, desc="Fetching teams and repos"
    )
    team_repo_tuples = [
        (team, list(api.get_team_repos(team))) for team in fetched_teams
    ]
    fetched_repos = list(
        itertools.chain.from_iterable(repos for _, repos in team_repo_tuples)
    )
    fetched_repo_dict = {r.name: r for r in fetched_repos}

    missing = set(expected_repo_names) - set(fetched_repo_dict.keys())
    if missing:
        raise plug.NotFoundError(f"Can't find repos: {', '.join(missing)}")

    if double_blind_salt:
        fetched_repo_dict = _create_anonymized_repos(
            team_repo_tuples, double_blind_salt, api
        )

    for assignment_name in assignment_names:
        plug.echo("Allocating reviews")
        allocations = plug.manager.hook.generate_review_allocations(
            teams=teams, num_reviews=num_reviews
        )
        # adjust names of review teams
        review_team_specs, reviewed_team_names = list(
            zip(
                *[
                    (
                        plug.StudentTeam(
                            members=alloc.review_team.members,
                            name=_hash_if_salt(
                                plug.generate_review_team_name(
                                    str(alloc.reviewed_team), assignment_name
                                ),
                                salt=double_blind_salt,
                            ),
                        ),
                        alloc.reviewed_team,
                    )
                    for alloc in allocations
                ]
            )
        )

        review_teams = _repobee.command.teams.create_teams(
            review_team_specs, plug.TeamPermission.PULL, api
        )
        review_teams_progress = plug.cli.io.progress_bar(
            review_teams,
            desc="Creating review teams",
            total=len(review_team_specs),
        )

        for review_team, reviewed_team_name in zip(
            review_teams_progress, reviewed_team_names
        ):
            reviewed_repo = fetched_repo_dict[
                plug.generate_repo_name(reviewed_team_name, assignment_name)
            ]

            review_teams_progress.write(  # type: ignore
                f"Assigning {' and '.join(review_team.members)} "
                f"to review {reviewed_repo.name}"
            )
            api.assign_repo(
                review_team, reviewed_repo, plug.TeamPermission.PULL
            )
            api.create_issue(
                issue.title,
                issue.body,
                reviewed_repo,
                # It's not possible to assign users with read-access in Gitea
                # FIXME redesign so Gitea does not require special handling
                assignees=review_team.members
                if not isinstance(api, _repobee.ext.gitea.GiteaAPI)
                else None,
            )


def _create_anonymized_repos(
    team_repo_tuples: List[Tuple[plug.Team, List[plug.Repo]]],
    salt: str,
    api: plug.PlatformAPI,
) -> Dict[str, plug.Repo]:
    """Create anonymous copies of the given repositories, push them to the
    platform and return a mapping from repo name to platform repo.
    """
    with tempfile.TemporaryDirectory() as tmp_clone_dir, tempfile.TemporaryDirectory() as tmp_workdir:  # noqa
        workdir = pathlib.Path(tmp_workdir)
        clone_dir = pathlib.Path(tmp_clone_dir)
        student_repos = _clone_to_student_repos(
            team_repo_tuples, workdir, clone_dir, api
        )
        student_repos_iter = plug.cli.io.progress_bar(
            student_repos, desc="Creating anonymized repos"
        )
        repo_mapping = {}
        anonymized_repos = []
        for student_repo in student_repos_iter:
            anon_student_repo, anon_platform_repo = _create_anonymized_repo(
                student_repo, salt, api
            )
            anonymized_repos.append(anon_student_repo)
            repo_mapping[student_repo.name] = anon_platform_repo

        _push_to_platform(anonymized_repos, api)

        return repo_mapping


def _create_anonymized_repo(
    student_repo: plug.StudentRepo, salt: str, api: plug.PlatformAPI
) -> Tuple[plug.StudentRepo, plug.Repo]:
    anonymized_repo_name = _hash_if_salt(student_repo.name, salt=salt)
    platform_repo = api.create_repo(
        name=anonymized_repo_name, description="Review copy", private=True
    )
    _anonymize_commit_history(student_repo.path)
    return (
        plug.StudentRepo(
            name=anonymized_repo_name,
            team=student_repo.team,
            url=student_repo.url.replace(
                student_repo.name, anonymized_repo_name
            ),
            _path=student_repo.path,
        ),
        platform_repo,
    )


def _anonymize_commit_history(repo_path: pathlib.Path) -> None:
    shutil.rmtree(repo_path / ".git")
    repo = git.Repo.init(repo_path)
    repo.git.add(".", "--force")
    repo.git.commit("-m", "Add project")
    repo.git.checkout(_DEFAULT_BRANCH)


def _clone_to_student_repos(
    team_repo_tuples: List[Tuple[plug.Team, List[plug.Repo]]],
    workdir: pathlib.Path,
    clone_dir: pathlib.Path,
    api: plug.PlatformAPI,
) -> List[plug.StudentRepo]:
    student_repos = [
        plug.StudentRepo(
            name=repo.name,
            team=plug.StudentTeam(name=team.name, members=list(team.members)),
            url=repo.url,
            _path=workdir / team.name / repo.name,
        )
        for team, repos in team_repo_tuples
        for repo in repos
    ]
    list(
        _repobee.git.clone_student_repos(
            student_repos, clone_dir, update_local=False, api=api
        )
    )
    return student_repos


def _push_to_platform(
    student_repos: List[plug.StudentRepo], api: plug.PlatformAPI
) -> None:
    push_tuples = [
        _repobee.git.Push(
            repo.path, api.insert_auth(repo.url), _DEFAULT_BRANCH
        )
        for repo in student_repos
    ]
    _repobee.git.push(push_tuples)


def _hash_if_salt(s: str, salt: Optional[str], max_hash_size: int = 20) -> str:
    """Hash the string with the salt, if provided. Otherwise, return the input
    string.
    """
    return _repobee.hash.salted_hash(s, salt, max_hash_size) if salt else s


def purge_review_teams(
    assignment_names: Iterable[str],
    students: Iterable[plug.StudentTeam],
    api: plug.PlatformAPI,
) -> None:
    """Delete all review teams associated with the given assignment names and
    student teams.

    Args:
        assignment_names: Names of assignments.
        students: An iterble of student teams.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.
    """
    review_team_names = [
        plug.generate_review_team_name(student, assignment_name)
        for student in students
        for assignment_name in assignment_names
    ]
    teams = progresswrappers.get_teams(
        review_team_names, api, desc="Deleting review teams"
    )
    for team in teams:
        api.delete_team(team)
        plug.log.info(f"Deleted {team.name}")


def check_peer_review_progress(
    assignment_names: Iterable[str],
    teams: Iterable[plug.Team],
    title_regex: str,
    num_reviews: int,
    api: plug.PlatformAPI,
) -> None:
    """Check which teams have opened peer review issues in their allotted
    review repos

    Args:
        assignment_names: Names of assignments.
        teams: An iterable of student teams.
        title_regex: A regex to match against issue titles.
        num_reviews: Amount of reviews each student is expected to have made.
        api: An implementation of :py:class:`repobee_plug.PlatformAPI` used to
            interface with the platform (e.g. GitHub or GitLab) instance.

    """
    teams = list(teams)
    reviews = collections.defaultdict(list)

    review_team_names = [
        plug.generate_review_team_name(team, assignment_name)
        for team in teams
        for assignment_name in assignment_names
    ]

    review_teams = progresswrappers.get_teams(
        review_team_names, api, desc="Processing review teams"
    )
    for review_team in review_teams:
        repos = list(api.get_team_repos(review_team))
        if len(repos) != 1:
            plug.log.warning(
                f"Expected {review_team.name} to have 1 associated "
                f"repo, found {len(repos)}. "
                f"Skipping..."
            )
            continue

        reviewed_repo = repos[0]
        expected_reviewers = set(review_team.members)
        reviewing_teams = _extract_reviewing_teams(teams, expected_reviewers)

        review_issue_authors = {
            issue.author
            for issue in api.get_repo_issues(reviewed_repo)
            if re.match(title_regex, issue.title)
        }

        for team in reviewing_teams:
            reviews[str(team)].append(
                plug.Review(
                    repo=reviewed_repo.name,
                    done=any(
                        map(review_issue_authors.__contains__, team.members)
                    ),
                )
            )

    plug.echo(
        formatters.format_peer_review_progress_output(
            reviews, [team.name for team in teams], num_reviews
        )
    )


def _extract_reviewing_teams(teams, reviewers):
    review_teams = []
    for team in teams:
        if any(map(team.members.__contains__, reviewers)):
            review_teams.append(team)
    return review_teams
