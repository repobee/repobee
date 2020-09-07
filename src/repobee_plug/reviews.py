"""Containers and helpers for peer review plugins."""
import collections


ReviewAllocation = collections.namedtuple(
    "ReviewAllocation", "review_team reviewed_team"
)
ReviewAllocation.__doc__ = """
Args:
    review_team (Team): The team of reviewers.
    reviewed_team (Team): The team that is to be reviewed.
"""

Review = collections.namedtuple("Review", ["repo", "done"])
Review.__doc__ = """
Args:
    repo (Repo): The reviewed repository.
    done (bool): Whether or not the review is done.
"""
