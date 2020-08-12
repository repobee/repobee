"""The default implementation of generate_review_allocations.

.. module:: genreviews
    :synopsis: The default implementation of generate_review_allocations

.. moduleauthor:: Simon Larsén
"""
import random
import itertools
from typing import List

import repobee_plug as plug


@plug.repobee_hook
def generate_review_allocations(
    teams: List[plug.StudentTeam], num_reviews: int
) -> List[plug.ReviewAllocation]:
    if num_reviews >= len(teams):
        raise ValueError("num_reviews must be less than len(teams)")
    if num_reviews <= 0:
        raise ValueError("num_reviews must be greater than 0")
    if len(teams) < 2:
        raise ValueError(
            "there must be at least 2 teams for peer review, "
            "but {} were provided".format(len(teams))
        )

    random.shuffle(teams)

    # create a list of lists, where each non-first list is a left-shifted
    # version of the previous list (lists wrap around)
    # e.g. for teams [4, 3, 1] and num_reviews = 2, the result is
    # allocations = [[4, 3, 1], [3, 1, 4], [1, 4, 3]] and means that
    # student 4 gets reviewed by 3 and 1, 3 by 1 and 4 etc.
    allocations = [teams]
    for _ in range(num_reviews):
        next_reviewers = list(allocations[-1])
        next_reviewers.append(next_reviewers.pop(0))  # shift list left
        allocations.append(next_reviewers)

    def merge_teams(teams):
        members = list(
            itertools.chain.from_iterable([team.members for team in teams])
        )
        return plug.StudentTeam(members=members)

    transposed_allocations = zip(*allocations)
    review_allocations = [
        plug.ReviewAllocation(
            review_team=merge_teams(reviewers), reviewed_team=reviewed_team
        )
        for reviewed_team, *reviewers in transposed_allocations
    ]

    return review_allocations
