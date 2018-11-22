"""The defaults plugin contains all default hook implementations.

The goal is to make core parts of repomate pluggable using hooks that only
return the first result that is not None. The standard behavior will be provided
by the default plugin (this one), which implements all of the required hooks.
The default plugin will always be run last, so any user-defined hooks will run
before it and therefore effectively override the default hooks.

Currently, only the peer review related generate_review_allocations hook has a
default implementation.

.. module:: defaults
    :synopsis: Plugin that provides the default behavior for core repomate
        functionality.

.. moduleauthor:: Simon Larsén
"""
import random
from typing import Callable, Iterable, Mapping, List

import daiquiri

from repomate_plug import repomate_hook

LOGGER = daiquiri.getLogger(name=__file__)


@repomate_hook
def generate_review_allocations(
        master_repo_name: str, students: Iterable[str], num_reviews: int,
        review_team_name_function: Callable[[str, str], str]
) -> Mapping[str, List[str]]:
    """Generate a (peer_review_team -> reviewers) mapping for each student
    repository (i.e. <student>-<master_repo_name>), where len(reviewers) =
    num_reviews.

    review_team_name_function should be used to generate review team names.
    It should be called like:

    .. code-block:: python
        
        review_team_name_function(master_repo_name, student)

    .. important::
            
        There must be strictly more students than reviewers per repo
        (`num_reviews`). Otherwise, allocation is impossible.

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
    if num_reviews >= len(students):
        raise ValueError("num_reviews must be less than len(students)")
    if num_reviews <= 0:
        raise ValueError("num_reviews must be greater than 0")
    if len(students) < 2:
        raise ValueError(
            "there must be at least 2 students for peer review, but {} were provided"
            .format(len(students)))

    random.shuffle(students)

    # create a list of lists, where each non-first list is a left-shifted
    # version of the previous list (lists wrap around)
    # e.g. for students [4, 3, 1] and num_reviews = 2, the result is
    # allocations = [[4, 3, 1], [3, 1, 4], [1, 4, 3]] and means that
    # student 4 gets reviewed by 3 and 1, 3 by 1 and 4 etc.
    allocations = [students]
    for _ in range(num_reviews):
        next_reviewers = list(allocations[-1])
        next_reviewers.append(next_reviewers.pop(0))  # shift list left
        allocations.append(next_reviewers)

    review_allocations = {
        review_team_name_function(reviewee, master_repo_name): reviewers
        for reviewee, *reviewers in zip(*allocations)
    }

    return review_allocations
