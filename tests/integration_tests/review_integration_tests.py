"""Integration tests for the review commands."""
import re

import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestAssignReviews:
    """Tests for the assign-reviews command."""

    def test_assign_one_review(self, with_student_repos, extra_args):
        master_repo_name = MASTER_REPO_NAMES[1]
        expected_review_teams = [
            plug.Team(
                members=[],
                name=plug.generate_review_team_name(
                    student_team_name, master_repo_name
                ),
            )
            for student_team_name in STUDENT_TEAM_NAMES
        ]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.ASSIGN_REVIEWS_PARSER,
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
                "-n",
                "1",
            ]
        )
        group_assertion = expected_num_members_group_assertion(
            expected_num_members=1
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_on_groups(
            expected_review_teams, single_group_assertion=group_assertion
        )
        asserts.assert_num_issues(STUDENT_TEAMS, [master_repo_name], 1)
        asserts.assert_issues_exist(
            STUDENT_TEAMS,
            [master_repo_name],
            _repobee.ext.gitlab.DEFAULT_REVIEW_ISSUE,
            expected_num_asignees=1,
        )

    def test_assign_to_nonexisting_students(
        self, with_student_repos, extra_args
    ):
        """If you try to assign reviews where one or more of the allocated
        student repos don't exist, there should be an error.
        """
        master_repo_name = MASTER_REPO_NAMES[1]
        non_existing_group = "non-existing-group"
        student_team_names = STUDENT_TEAM_NAMES + [non_existing_group]

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.ASSIGN_REVIEWS_PARSER,
                *BASE_ARGS_NO_TB,
                "--mn",
                master_repo_name,
                "-s",
                *student_team_names,
                "-n",
                "1",
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        output = result.stdout.decode("utf-8")

        assert (
            "[ERROR] NotFoundError: Can't find repos: {}".format(
                plug.generate_repo_name(non_existing_group, master_repo_name)
            )
            in output
        )
        assert result.returncode == 1
        asserts.assert_num_issues(STUDENT_TEAMS, [master_repo_name], 0)


@pytest.fixture
def with_reviews(with_student_repos):
    master_repo_name = MASTER_REPO_NAMES[1]
    expected_review_teams = [
        plug.Team(
            members=[],
            name=plug.generate_review_team_name(
                student_team_name, master_repo_name
            ),
        )
        for student_team_name in STUDENT_TEAM_NAMES
    ]
    command = " ".join(
        [
            REPOBEE_GITLAB,
            _repobee.cli.mainparser.ASSIGN_REVIEWS_PARSER,
            *BASE_ARGS,
            "--mn",
            master_repo_name,
            *STUDENTS_ARG,
            "-n",
            "1",
        ]
    )

    result = run_in_docker(command)

    assert result.returncode == 0
    asserts.assert_on_groups(
        expected_review_teams,
        single_group_assertion=expected_num_members_group_assertion(1),
    )
    return (master_repo_name, expected_review_teams)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestEndReviews:
    def test_end_all_reviews(self, with_reviews, extra_args):
        master_repo_name, review_teams = with_reviews
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.PURGE_REVIEW_TEAMS_PARSER,
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        def assert_no_actual_groups(expected, actual):
            assert not actual

        assert result.returncode == 0
        # student teams should still exist
        asserts.assert_on_groups(STUDENT_TEAMS)
        # review teams should not
        asserts.assert_on_groups(
            review_teams, all_groups_assertion=assert_no_actual_groups
        )

    def test_end_non_existing_reviews(self, with_reviews, extra_args):
        _, review_teams = with_reviews
        master_repo_name = MASTER_REPO_NAMES[0]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.PURGE_REVIEW_TEAMS_PARSER,
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_on_groups(STUDENT_TEAMS)
        asserts.assert_on_groups(
            review_teams,
            single_group_assertion=expected_num_members_group_assertion(1),
        )


class TestCheckReviews:
    """Tests for check-reviews command."""

    def test_no_reviews_opened(self, with_reviews, extra_args):
        master_repo_name, _ = with_reviews
        num_reviews = 0
        num_expected_reviews = 1
        master_repo_name = MASTER_REPO_NAMES[1]
        pattern_template = r"{}.*{}.*{}.*\w+-{}.*"
        expected_output_patterns = [
            pattern_template.format(
                team_name,
                str(num_reviews),
                str(num_expected_reviews - num_reviews),
                master_repo_name,
            )
            for team_name in STUDENT_TEAM_NAMES
        ]
        unexpected_output_patterns = [r"\[ERROR\]"]

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CHECK_REVIEW_PROGRESS_PARSER,
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
                "--num-reviews",
                str(num_expected_reviews),
                "--title-regex",
                "Review",
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        output = result.stdout.decode("utf-8")

        assert result.returncode == 0
        search_flags = re.MULTILINE
        for expected_pattern in expected_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)

    def test_expect_too_many_reviews(self, with_reviews, extra_args):
        """Test that warnings are printed if a student is assigned to fewer
        review teams than expected.
        """
        master_repo_name, _ = with_reviews
        num_reviews = 0
        actual_assigned_reviews = 1
        num_expected_reviews = 2
        master_repo_name = MASTER_REPO_NAMES[1]
        warning_template = (
            r"^\[WARNING\] Expected {} to be assigned to {} review teams, but "
            "found {}. Review teams may have been tampered with."
        )
        pattern_template = r"{}.*{}.*{}.*\w+-{}.*"
        expected_output_patterns = [
            pattern_template.format(
                team_name,
                str(num_reviews),
                str(actual_assigned_reviews - num_reviews),
                master_repo_name,
            )
            for team_name in STUDENT_TEAM_NAMES
        ] + [
            warning_template.format(
                team_name,
                str(num_expected_reviews),
                str(actual_assigned_reviews),
            )
            for team_name in STUDENT_TEAM_NAMES
        ]
        unexpected_output_patterns = [r"\[ERROR\]"]

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CHECK_REVIEW_PROGRESS_PARSER,
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
                "--num-reviews",
                str(num_expected_reviews),
                "--title-regex",
                "Review",
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        output = result.stdout.decode("utf-8")

        assert result.returncode == 0
        search_flags = re.MULTILINE
        for expected_pattern in expected_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)


def expected_num_members_group_assertion(expected_num_members):
    def group_assertion(expected, actual):
        assert expected.name == actual.name
        # +1 member for the group owner
        assert len(actual.members.list(all=True)) == expected_num_members + 1
        assert len(actual.projects.list(all=True)) == 1
        project_name = actual.projects.list(all=True)[0].name
        assert actual.name.startswith(project_name)
        for member in actual.members.list(all=True):
            if member.username == ACTUAL_USER:
                continue
            assert member.username not in project_name
            assert member.access_level == gitlab.REPORTER_ACCESS

    return group_assertion
