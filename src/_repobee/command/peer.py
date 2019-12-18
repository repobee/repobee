"""Top-level commands for peer reviewing.

This module contains the top-level functions for RepoBee's peer review
functionality. Each public function in this module is to be treated as a
self-contained program.

.. module:: peer
    :synopsis: Top-level commands for peer reviewing.

.. moduleauthor:: Simon Larsén
"""
from typing import Iterable, Optional

import repobee_plug as plug

from _repobee import formatters
from _repobee.command.repos import LOGGER


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
        api.ensure_teams_and_members(
            review_teams, permission=plug.TeamPermission.PULL
        )
        api.add_repos_to_review_teams(
            {
                review_team.name: [
                    plug.generate_repo_name(reviewed_team, master_name)
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
        plug.generate_review_team_name(student, master_repo_name)
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
        plug.generate_review_team_name(team, master_name)
        for team in teams
        for master_name in master_repo_names
    ]
    reviews = api.get_review_progress(review_team_names, teams, title_regex)

    LOGGER.info(
        formatters.format_peer_review_progress_output(
            reviews, teams, num_reviews
        )
    )
