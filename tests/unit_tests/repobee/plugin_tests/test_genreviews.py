"""Tests for the genreviews plugin."""
import itertools
import collections

import pytest

from _repobee.ext.defaults import genreviews

import constants


class TestGenerateReviewAllocations:
    """Tests the default implementation of generate_review_allocations."""

    @pytest.mark.parametrize("num_students, num_reviews", [(10, 10), (3, 15)])
    def test_raises_when_too_many_reviews(self, num_students, num_reviews):
        teams = list(constants.STUDENTS[:num_students])
        with pytest.raises(ValueError) as exc_info:
            genreviews.generate_review_allocations(teams, num_reviews)

        assert "num_reviews must be less than len(teams)" in str(
            exc_info.value
        )

    def test_raises_when_too_few_reviews(self):
        with pytest.raises(ValueError) as exc_info:
            genreviews.generate_review_allocations(list(constants.STUDENTS), 0)
        assert "num_reviews must be greater than 0" in str(exc_info.value)

    @pytest.mark.parametrize(
        "num_students, num_reviews", [(10, 4), (50, 13), (10, 1)]
    )
    def test_all_students_allocated_same_amount_of_times(
        self, num_students, num_reviews
    ):
        """All students should have to review precisely num_reviews repos."""
        students = list(constants.STUDENTS[:num_students])
        assert len(students) == num_students, "pre-test assert"

        allocations = genreviews.generate_review_allocations(
            students, num_reviews
        )

        # flatten the peer review lists
        peer_reviewers = list(
            itertools.chain.from_iterable(
                alloc.review_team.members for alloc in allocations
            )
        )
        counts = collections.Counter(peer_reviewers)

        assert len(peer_reviewers) == num_reviews * num_students
        assert all(map(lambda freq: freq == num_reviews, counts.values()))

    @pytest.mark.parametrize(
        "num_students, num_reviews", [(10, 4), (50, 3), (10, 1)]
    )
    def test_all_students_get_reviewed(self, num_students, num_reviews):
        """All students should get a review team."""
        teams = list(constants.STUDENTS[:num_students])
        expected_reviewed_teams = list(teams)

        allocations = genreviews.generate_review_allocations(
            teams, num_reviews
        )

        assert sorted(expected_reviewed_teams) == sorted(
            [alloc.reviewed_team for alloc in allocations]
        )
