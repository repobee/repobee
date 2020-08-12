"""A peer review plugin which attempts to assign pairwise peer reviews.
Intended for students to sit and discuss their code bases with each other, as
well as leave feedback. More specifically, N students are split into N/2
groups, each group member assigned to peer review the other person in the
group.

If N is odd, the students are split into (N-1)/2 groups, in which one group has
3 members.

.. module:: pairwise
    :synopsis: Plugin that provides pairwise peer review allocations.

.. moduleauthor:: Simon Larsén
"""
import random
from typing import List


import repobee_plug as plug

PLUGIN_DESCRIPTION = (
    "Makes peer review allocation pairwise (if student A reviews student B, "
    "then student B reviews student A)"
)


@plug.repobee_hook
def generate_review_allocations(
    teams: List[plug.StudentTeam], num_reviews: int = 1
) -> List[plug.ReviewAllocation]:
    """Generate peer review allocations such that if team_a reviews team_b,
    then team_b reviews team_a, and no others!

    The ``num_reviews`` argument is ignored by this plugin.

    Args:
        teams: Student teams for which to allocate reviews.
        num_reviews: Ignored by this plugin.
    Returns:
        A list of allocations that
    """
    teams = list(teams)
    if num_reviews != 1:
        plug.log.warning(
            "num_reviews specified to {}, but in pairwise assignment "
            "num_reviews is ignored".format(num_reviews)
        )
    if len(teams) < 2:
        raise ValueError(
            "there must be at least 2 teams for peer review, "
            "but {} were provided".format(len(teams))
        )

    random.shuffle(teams)

    groups = [(teams[i - 1], teams[i]) for i in range(1, len(teams), 2)]
    if len(teams) % 2:
        groups[-1] = (*groups[-1], teams[-1])

    allocations = []
    for group in groups:
        for i, review_team in enumerate(group):
            reviewed_team = group[(i + 1) % len(group)]
            allocations.append(
                plug.ReviewAllocation(
                    review_team=review_team, reviewed_team=reviewed_team
                )
            )
    return allocations
