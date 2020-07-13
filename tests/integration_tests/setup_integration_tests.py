import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestSetup:
    """Integration tests for the setup command."""

    def test_clean_setup(self, extra_args):
        """Test a first-time setup with master repos in the master org."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.SETUP_PARSER,
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        asserts.assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        asserts.assert_on_groups(STUDENT_TEAMS)

    def test_setup_twice(self, extra_args):
        """Setting up twice should have the same effect as setting up once."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.SETUP_PARSER,
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        asserts.assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        asserts.assert_on_groups(STUDENT_TEAMS)
