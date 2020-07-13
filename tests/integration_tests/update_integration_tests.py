"""Integration tests for the update command"""

import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *

@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestUpdate:
    """Integration tests for the update command."""

    def test_happy_path(self, with_student_repos, extra_args):
        master_repo = MASTER_REPO_NAMES[0]
        filename = "superfile.super"
        text = "some epic content\nfor this file!"
        update_repo(master_repo, filename, text)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.UPDATE_PARSER,
                *MASTER_ORG_ARG,
                *BASE_ARGS,
                "--mn",
                master_repo,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        asserts.assert_repos_contain(
            STUDENT_TEAMS, [master_repo], filename, text
        )

    def test_opens_issue_if_update_rejected(
        self, tmpdir, with_student_repos, extra_args
    ):
        master_repo = MASTER_REPO_NAMES[0]
        conflict_repo = plug.generate_repo_name(STUDENT_TEAMS[0], master_repo)
        filename = "superfile.super"
        text = "some epic content\nfor this file!"
        # update the master repo
        update_repo(master_repo, filename, text)
        # conflicting update in the student repo
        update_repo(conflict_repo, "somefile.txt", "some other content")

        issue = plug.Issue(title="Oops, push was rejected!", body="")
        issue_file = pathlib.Path(str(tmpdir)) / "issue.md"
        issue_file.write_text(issue.title)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.UPDATE_PARSER,
                *MASTER_ORG_ARG,
                *BASE_ARGS,
                "--mn",
                master_repo,
                *STUDENTS_ARG,
                "--issue",
                issue_file.name,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_repos_contain(
            STUDENT_TEAMS[1:], [master_repo], filename, text
        )
        asserts.assert_issues_exist(STUDENT_TEAMS[0:1], [master_repo], issue)
