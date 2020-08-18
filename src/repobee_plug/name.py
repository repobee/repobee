"""Utility functions relating to RepoBee's naming conventions.

.. module:: name
    :synopsis: Utility functions relating to RepoBee's naming conventions.
"""
from typing import Iterable


def generate_repo_names(
    team_names: Iterable[str], assignment_names: Iterable[str]
) -> Iterable[str]:
    """Construct all combinations of generate_repo_name(team_name,
    assignment_name) for the provided team names and master repo names.

    Args:
        team_names: One or more names of teams.
        assignment_names: One or more names of assignments.

    Returns:
        a list of repo names for all combinations of team and master repo.
    """
    assignment_names = list(
        assignment_names
    )  # needs to be traversed multiple times
    return [
        generate_repo_name(team_name, master_name)
        for master_name in assignment_names
        for team_name in team_names
    ]


def generate_repo_name(team_name: str, assignment_name: str) -> str:
    """Construct a repo name for a team.

    Args:
        team_name: Name of the associated team.
        assignment_name: Name of an assignment.
    """
    return "{}-{}".format(team_name, assignment_name)


def generate_review_team_name(student: str, assignment_name: str) -> str:
    """Generate a review team name.

    Args:
        student: A student username.
        assignment_name: Name of an assignment.

    Returns:
        a review team name for the student repo associated with this master
        repo and student.
    """
    return generate_repo_name(student, assignment_name) + "-review"
