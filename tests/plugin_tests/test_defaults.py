"""Tests for the defaults plugin."""
import string
import itertools
import collections

import pytest

from repobee import util
from repobee.ext import defaults


class TestGenerateReviewAllocations:
    """Tests the default implementation of generate_review_allocations."""

    @pytest.mark.parametrize(
        "num_students, num_reviews", [(10, 10), (3, 15), (0, 0)]
    )
    def test_throws_when_too_many_reviews(
        self, num_students, num_reviews, students
    ):
        corrected_students = students[:num_students]
        assert len(corrected_students) == num_students, "pre-test assert"

        master_repo_name = "week-2"
        with pytest.raises(ValueError) as exc_info:
            defaults.generate_review_allocations(
                master_repo_name,
                corrected_students,
                num_reviews,
                util.generate_review_team_name,
            )

        assert "num_reviews must be less than len(students)" in str(exc_info)

    def test_throws_when_too_few_reviews(self, students):
        with pytest.raises(ValueError) as exc_info:
            defaults.generate_review_allocations(
                "week-2", students, 0, util.generate_review_team_name
            )
        assert "num_reviews must be greater than 0" in str(exc_info)

    @pytest.mark.parametrize(
        "num_students, num_reviews", [(10, 4), (50, 13), (10, 1)]
    )
    def test_all_students_allocated_same_amount_of_times(
        self, num_students, num_reviews, students
    ):
        """All students should have to review precisely num_reviews repos."""
        corrected_students = students[:num_students]
        assert len(corrected_students) == num_students, "pre-test assert"

        allocations = defaults.generate_review_allocations(
            "week-2",
            corrected_students,
            num_reviews,
            util.generate_review_team_name,
        )

        # flatten the peer review lists
        peer_reviewers = list(
            itertools.chain.from_iterable(
                reviewers for reviewers in allocations.values()
            )
        )
        counts = collections.Counter(peer_reviewers)

        assert len(peer_reviewers) == num_reviews * num_students
        assert all(map(lambda freq: freq == num_reviews, counts.values()))

    @pytest.mark.parametrize(
        "num_students, num_reviews", [(10, 4), (50, 3), (10, 1)]
    )
    def test_all_students_get_reviewed(
        self, num_students, num_reviews, students
    ):
        """All students should get a review team."""
        corrected_students = students[:num_students]
        master_repo_name = "week-5"
        assert len(corrected_students) == num_students, "pre-test assert"

        expected_review_teams = [
            util.generate_review_team_name(student, master_repo_name)
            for student in corrected_students
        ]

        allocations = defaults.generate_review_allocations(
            master_repo_name,
            corrected_students,
            num_reviews,
            util.generate_review_team_name,
        )

        assert set(expected_review_teams) == set(allocations.keys())
