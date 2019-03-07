"""Tests for the pairwise plugin."""
import string
import itertools
import collections

import pytest

from repomate import util
from repomate.plugin import register_plugins
from repomate.ext import pairwise


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
        students = list(string.ascii_letters[:num_students])
        assert len(students) == num_students, "pre-test assert"

        allocations = pairwise.generate_review_allocations(
            "week-2", students, util.generate_review_team_name, num_reviews
        )

        # flatten the peer review lists
        peer_reviewers = list(
            itertools.chain.from_iterable(
                reviewers for reviewers in allocations.values()
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
        students = string.ascii_letters[:num_students]
        master_repo_name = "week-5"
        assert len(students) == num_students, "pre-test assert"

        expected_review_teams = [
            util.generate_review_team_name(student, master_repo_name)
            for student in students
        ]

        allocations = pairwise.generate_review_allocations(
            master_repo_name,
            students,
            util.generate_review_team_name,
            num_reviews,
        )

        assert set(expected_review_teams) == set(allocations.keys())

    @pytest.mark.parametrize(
        "num_students, num_reviews",
        [(10, 4), (50, 13), (10, 1), (13, 2), (27, 1)],
    )
    def test_students_dont_review_themselves(self, num_students, num_reviews):
        """All students should get a review team."""
        students = string.ascii_letters[:num_students]
        master_repo_name = "week-5"
        assert len(students) == num_students, "pre-test assert"

        expected_review_teams = [
            util.generate_review_team_name(student, master_repo_name)
            for student in students
        ]

        allocations = pairwise.generate_review_allocations(
            master_repo_name,
            students,
            util.generate_review_team_name,
            num_reviews,
        )

        assert set(expected_review_teams) == set(allocations.keys())
        for review_team, (reviewer, *_) in allocations.items():
            # exploit that students are single letters
            # TODO make more robust
            reviewed_student = review_team[0]
            assert reviewed_student != reviewer

    @pytest.mark.parametrize("num_students", [4, 10, 32, 50])
    def test_all_groups_size_2_with_even_amount_of_students(
        self, num_students
    ):
        students = string.ascii_letters[:num_students]
        master_repo_name = "week-5"
        assert len(students) == num_students, "pre-test assert"

        allocations = pairwise.generate_review_allocations(
            master_repo_name,
            students,
            num_reviews=1,
            review_team_name_function=util.generate_review_team_name,
        )

        # exploit that each student is represented by a single letter
        # TODO make more robust
        for review_team, (reviewer, *_) in allocations.items():
            reviewed_student = review_team[0]
            expected_counter_team = util.generate_review_team_name(
                reviewer, master_repo_name
            )
            assert allocations[expected_counter_team][0] == reviewed_student
        assert len(allocations) == num_students
