"""Tests for the pairwise plugin."""
import itertools
import collections

import pytest

import repobee_plug as plug

from _repobee.plugin import register_plugins
from _repobee.ext import pairwise


from repobee_testhelpers._internal import constants


class TestGenerateReviewAllocations:
    """Tests the default implementation of generate_review_allocations."""

    def test_register(self):
        register_plugins([pairwise])

    @pytest.mark.parametrize(
        "num_students, num_reviews",
        [(10, 4), (50, 13), (10, 1), (13, 2), (27, 1)],
    )
    def test_all_students_allocated_single_review(
        self, num_students, num_reviews
    ):
        """All students should have to review precisely 1 repo.
        num_reviews should be ignored.
        """
        teams = list(constants.STUDENTS[:num_students])

        allocations = pairwise.generate_review_allocations(teams, num_reviews)

        # flatten the peer review lists
        peer_reviewers = list(
            itertools.chain.from_iterable(
                alloc.review_team.members for alloc in allocations
            )
        )
        counts = collections.Counter(peer_reviewers)

        assert len(peer_reviewers) == num_students
        assert all(map(lambda freq: freq == 1, counts.values()))

    @pytest.mark.parametrize(
        "num_students, num_reviews",
        [(10, 4), (50, 13), (10, 1), (13, 2), (27, 1)],
    )
    def test_all_students_get_reviewed(self, num_students, num_reviews):
        """All students should get a review team."""
        teams = list(constants.STUDENTS[:num_students])
        expected_reviewed_teams = list(teams)

        allocations = pairwise.generate_review_allocations(teams, num_reviews)

        assert sorted(expected_reviewed_teams) == sorted(
            [alloc.reviewed_team for alloc in allocations]
        )

    @pytest.mark.parametrize(
        "num_students, num_reviews",
        [(10, 4), (50, 13), (10, 1), (13, 2), (27, 1)],
    )
    def test_students_dont_review_themselves(self, num_students, num_reviews):
        teams = list(constants.STUDENTS[:num_students])

        allocations = pairwise.generate_review_allocations(teams, num_reviews)

        for review_team, reviewed_team in allocations:
            assert not set(review_team.members).intersection(
                reviewed_team.members
            )

    @pytest.mark.parametrize("num_students", [4, 10, 32, 50])
    def test_all_students_paired_up_with_even_amount_of_students(
        self, num_students
    ):
        teams = constants.STUDENTS[:num_students]

        allocations = pairwise.generate_review_allocations(
            teams, num_reviews=1
        )

        assert len(allocations) == num_students
        for review_team, reviewed_team in allocations:
            expected_counter_review = plug.ReviewAllocation(
                review_team=reviewed_team, reviewed_team=review_team
            )
            assert allocations.index(expected_counter_review) >= 0
