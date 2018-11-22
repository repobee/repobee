"""A peer review plugin which attempts to assign pairwise peer reviews.
Intended for students to sit and discuss their code bases with each other, as
well as leave feedback. More specifically, N students are split into N/2 groups,
each group member assigned to peer review the other person in the group.

If N is odd, the students are split into (N-1)/2 groups, in which one group has
3 members.

.. module:: pairwise
    :synopsis: Plugin that provides pairwise peer review allocations.

.. moduleauthor:: Simon Larsén
"""
import random
from typing import Callable, Iterable, Mapping, List

import daiquiri

from repomate_plug import repomate_hook

LOGGER = daiquiri.getLogger(name=__file__)


@repomate_hook
def generate_review_allocations(
        master_repo_name: str,
        students: Iterable[str],
        num_reviews: int = None,
        review_team_name_function: Callable[[str, str], str] = None
) -> Mapping[str, List[str]]:
    """Generate a (peer_review_team -> reviewers) mapping for each student
    repository (i.e. <student>-<master_repo_name>), where len(reviewers) =
    1 or 2.

    The ``num_reviews`` argument is ignored by this plugin.

    Args:
        master_repo_name: Name of a master repository.
        students: Students for which to generate peer review allocations.
        num_reviews: Amount of reviews each student should perform (and
        consequently amount of reviewers per repo)
        review_team_name_function: A function that takes a master repo name
        as its first argument, and a student username as its second, and
        returns a review team name.
    Returns:
        a (peer_review_team -> reviewers) mapping for each student repository.
    """
    students = list(students)
    if num_reviews != 1:
        LOGGER.warning(
            "num_reviews specified to {}, but in pairwise assignment num_reviews is ignored"
            .format(num_reviews))
    if len(students) < 2:
        raise ValueError(
            "there must be at least 2 students for peer review, but {} were provided"
            .format(len(students)))

    random.shuffle(students)

    groups = [(students[i - 1], students[i])
              for i in range(1, len(students), 2)]
    if len(students) % 2:
        groups[-1] = (*groups[-1], students[-1])

    allocations = {}
    for group in groups:
        for i, reviewer in enumerate(group):
            student = group[(i + 1) % len(group)]
            allocations[review_team_name_function(student,
                                                  master_repo_name)] = [reviewer]
    return allocations
