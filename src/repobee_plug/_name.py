"""Utility functions relating to RepoBee's naming conventions.

.. module:: name
    :synopsis: Utility functions relating to RepoBee's naming conventions.

.. moduleauthor:: Simon Larsén
"""
from typing import Iterable


def generate_repo_names(
    team_names: Iterable[str], master_repo_names: Iterable[str]
) -> Iterable[str]:
    """Construct all combinations of generate_repo_name(team_name,
    master_repo_name) for the provided team names and master repo names.

    Args:
        team_names: One or more names of teams.
        master_repo_names: One or more names of master repositories.

    Returns:
        a list of repo names for all combinations of team and master repo.
    """
    master_repo_names = list(
        master_repo_names
    )  # needs to be traversed multiple times
    return [
        generate_repo_name(team_name, master_name)
        for master_name in master_repo_names
        for team_name in team_names
    ]


def generate_repo_name(team_name: str, master_repo_name: str) -> str:
    """Construct a repo name for a team.

    Args:
        team_name: Name of the associated team.
        master_repo_name: Name of the template repository.
    """
    return "{}-{}".format(team_name, master_repo_name)


def generate_review_team_name(student: str, master_repo_name: str) -> str:
    """Generate a review team name.

    Args:
        student: A student username.
        master_repo_name: Name of a master repository.

    Returns:
        a review team name for the student repo associated with this master
        repo and student.
    """
    return generate_repo_name(student, master_repo_name) + "-review"
