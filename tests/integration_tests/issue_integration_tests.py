"""Integration tests for the issue commands."""

import re

import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestOpenIssues:
    """Tests for the open-issues command."""

    _ISSUE = plug.Issue(title="This is a title", body="This is a body")

    def test_happy_path(self, tmpdir_volume_arg, tmpdir, extra_args):
        """Test opening an issue in each student repo."""
        filename = "issue.md"
        text = "{}\n{}".format(self._ISSUE.title, self._ISSUE.body)
        tmpdir.join(filename).write_text(text, encoding="utf-8")

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.OPEN_ISSUE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-i",
                "{}/{}".format(VOLUME_DST, filename),
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_num_issues(STUDENT_TEAMS, MASTER_REPO_NAMES, 1)
        asserts.assert_issues_exist(
            STUDENT_TEAMS, MASTER_REPO_NAMES, self._ISSUE
        )


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestCloseIssues:
    """Tests for the close-issues command."""

    def test_closes_only_matched_issues(self, open_issues, extra_args):
        """Test that close-issues respects the regex."""
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        close_issue = open_issues[0]
        open_issue = open_issues[1]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLOSE_ISSUE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-r",
                close_issue.title,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_issues_exist(
            STUDENT_TEAM_NAMES,
            MASTER_REPO_NAMES,
            close_issue,
            expected_state="closed",
        )
        asserts.assert_issues_exist(
            STUDENT_TEAM_NAMES,
            MASTER_REPO_NAMES,
            open_issue,
            expected_state="opened",
        )


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestListIssues:
    """Tests for the list-issues command."""

    @pytest.mark.parametrize("discover_repos", [False, True])
    def test_lists_matching_issues(
        self, open_issues, extra_args, discover_repos
    ):
        # arrange
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        matched = open_issues[0]
        unmatched = open_issues[1]
        repo_names = plug.generate_repo_names(STUDENT_TEAMS, MASTER_REPO_NAMES)

        issue_pattern_template = r"^\[INFO\].*{}/#\d:\s+{}.*by {}.?$"
        expected_issue_output_patterns = [
            issue_pattern_template.format(
                repo_name, matched.title, ACTUAL_USER
            )
            for repo_name in repo_names
        ]
        unexpected_issue_output_patterns = [
            issue_pattern_template.format(
                repo_name, unmatched.title, ACTUAL_USER
            )
            for repo_name in repo_names
        ] + [
            r"\[ERROR\]"
        ]  # any kind of error is bad

        repo_arg = ["--discover-repos"] if discover_repos else MASTER_REPOS_ARG
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.LIST_ISSUES_PARSER,
                *BASE_ARGS,
                *repo_arg,
                *STUDENTS_ARG,
                "-r",
                matched.title,
            ]
        )

        # act
        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        output = result.stdout.decode("utf-8")

        # assert
        assert result.returncode == 0
        search_flags = re.MULTILINE
        for expected_pattern in expected_issue_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_issue_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)
