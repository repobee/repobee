"""Tests for the defaults plugin."""
import string
import itertools
import collections

import pytest

from repomate import util
from repomate.ext import defaults


class TestGenerateReviewAllocations:
    """Tests the default implementation of generate_review_allocations."""

    @pytest.mark.parametrize("num_students, num_reviews", [(10, 10), (3, 15), (0, 0)])
    def test_throws_when_too_many_reviews(self, num_students, num_reviews):
        master_repo_name = "week-2"
        students = list(string.ascii_lowercase[:num_students])
        with pytest.raises(ValueError) as exc_info:
            defaults.generate_review_allocations(
                master_repo_name, students, num_reviews, util.generate_review_team_name
            )

        assert "num_reviews must be less than len(students)" in str(exc_info)

    def test_throws_when_too_few_reviews(self):
        with pytest.raises(ValueError) as exc_info:
            defaults.generate_review_allocations(
                "week-2",
                list(string.ascii_lowercase),
                0,
                util.generate_review_team_name,
            )
        assert "num_reviews must be greater than 0" in str(exc_info)

    @pytest.mark.parametrize("num_students, num_reviews", [(10, 4), (50, 13), (10, 1)])
    def test_all_students_allocated_same_amount_of_times(
        self, num_students, num_reviews
    ):
        """All students should have to review precisely num_reviews repos."""
        students = list(string.ascii_letters[:num_students])
        assert len(students) == num_students, "pre-test assert"

        allocations = defaults.generate_review_allocations(
            "week-2", students, num_reviews, util.generate_review_team_name
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

    @pytest.mark.parametrize("num_students, num_reviews", [(10, 4), (50, 3), (10, 1)])
    def test_all_students_get_reviewed(self, num_students, num_reviews):
        """All students should get a review team."""
        students = string.ascii_letters[:num_students]
        master_repo_name = "week-5"
        assert len(students) == num_students, "pre-test assert"

        expected_review_teams = [
            util.generate_review_team_name(student, master_repo_name)
            for student in students
        ]

        allocations = defaults.generate_review_allocations(
            master_repo_name, students, num_reviews, util.generate_review_team_name
        )

        assert set(expected_review_teams) == set(allocations.keys())
