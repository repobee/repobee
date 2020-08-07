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
from typing import Iterable, Optional

import repobee_plug as plug

import _repobee.command.teams
from _repobee import formatters
from _repobee.command.repos import LOGGER

DEFAULT_REVIEW_ISSUE = plug.Issue(
    title="Peer review",
    body="You have been assigned to peer review this repo.",
)


def assign_peer_reviews(
    master_repo_names: Iterable[str],
    teams: Iterable[plug.Team],
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
    issue = issue or DEFAULT_REVIEW_ISSUE
    expected_repo_names = plug.generate_repo_names(teams, master_repo_names)

    fetched_teams = api.get_teams([t.name for t in teams])
    fetched_repos = list(
        itertools.chain.from_iterable(map(api.get_team_repos, fetched_teams))
    )
    fetched_repo_dict = {r.name: r for r in fetched_repos}

    missing = set(expected_repo_names) - set(fetched_repo_dict.keys())
    if missing:
        raise plug.NotFoundError(f"Can't find repos: {', '.join(missing)}")

    for master_name in master_repo_names:
        allocations = plug.manager.hook.generate_review_allocations(
            teams=teams, num_reviews=num_reviews
        )
        # adjust names of review teams
        review_team_specs, reviewed_team_names = list(
            zip(
                *[
                    (
                        plug.Team(
                            members=alloc.review_team.members,
                            name=plug.generate_review_team_name(
                                str(alloc.reviewed_team), master_name
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

        for review_team, reviewed_team_name in zip(
            review_teams, reviewed_team_names
        ):
            reviewed_repo = fetched_repo_dict[
                plug.generate_repo_name(reviewed_team_name, master_name)
            ]
            api.assign_repo(
                review_team, reviewed_repo, plug.TeamPermission.PULL
            )
            api.create_issue(
                issue.title,
                issue.body,
                reviewed_repo,
                assignees=review_team.members,
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
        plug.generate_review_team_name(student, master_repo_name)
        for student in students
        for master_repo_name in master_repo_names
    ]
    teams = api.get_teams(review_team_names)
    for team in teams:
        api.delete_team(team)
        LOGGER.info(f"Deleted {team.name}")


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
    teams = list(teams)
    reviews = collections.defaultdict(list)

    review_team_names = [
        plug.generate_review_team_name(team, master_name)
        for team in teams
        for master_name in master_repo_names
    ]

    for review_team in api.get_teams(review_team_names):
        repos = list(api.get_team_repos(review_team))
        if len(repos) != 1:
            LOGGER.warning(
                f"Expected {review_team.name} to have 1 associated "
                f"repo, found {len(review_team.repos)}. "
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
                        map(review_issue_authors.__contains__, team.members,)
                    ),
                )
            )

    LOGGER.info(
        formatters.format_peer_review_progress_output(
            reviews, teams, num_reviews
        )
    )


def _extract_reviewing_teams(teams, reviewers):
    review_teams = []
    for team in teams:
        if any(map(team.members.__contains__, reviewers)):
            review_teams.append(team)
    return review_teams
