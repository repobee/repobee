"""Tests for the issues category of commands."""
import pathlib
import pytest
import tempfile
import collections

import repobee_plug as plug
from repobee_plug.testhelpers import funcs
from repobee_plug.testhelpers.const import (
    TEMPLATE_REPOS_ARG,
    TEMPLATE_REPO_NAMES,
    STUDENTS_FILE,
    STUDENT_TEAMS,
    TARGET_ORG_NAME,
    TEACHER,
)

_TestIssue = collections.namedtuple("_TestIssue", "title body path")


@pytest.fixture
def issue():
    title = "This is the title"
    body = "And this\nis the body."
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "issue.md"
        path.write_text(f"{title}\n{body}")
        yield _TestIssue(title, body, path)


class TestOpen:
    """Tests for the ``issues open`` command."""

    def test_open_issue_for_all_repos(
        self, with_student_repos, platform_dir, platform_url, issue
    ):
        expected_repo_names = plug.generate_repo_names(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES
        )

        funcs.run_repobee(
            f"issues open --master-repo-names {TEMPLATE_REPOS_ARG} "
            f"--students-file {STUDENTS_FILE} "
            f"--base-url {platform_url} "
            f"--org-name {TARGET_ORG_NAME} "
            f"--user {TEACHER} "
            f"--issue {issue.path} "
        )

        repos = funcs.get_repos(platform_url, TARGET_ORG_NAME)
        issues_dict = {repo.name: repo.issues for repo in repos}

        num_asserts = 0
        for name in expected_repo_names:
            num_asserts += 1
            issues = issues_dict[name]
            first_issue = issues[0]

            assert len(issues) == 1
            assert first_issue.title == issue.title
            assert first_issue.body == issue.body
            assert first_issue.state == plug.IssueState.OPEN

        assert num_asserts == len(expected_repo_names)
