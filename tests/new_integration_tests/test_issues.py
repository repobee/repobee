"""Tests for the issues category of commands."""
import pathlib
import pytest
import tempfile
import collections

import repobee_plug as plug
from repobee_testhelpers import funcs
from repobee_testhelpers import const

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
        self, with_student_repos, platform_url, issue
    ):
        expected_repo_names = plug.generate_repo_names(
            const.STUDENT_TEAMS, const.TEMPLATE_REPO_NAMES
        )

        funcs.run_repobee(
            f"issues open --master-repo-names {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            f"--issue {issue.path} "
        )

        repos = funcs.get_repos(platform_url, const.TARGET_ORG_NAME)
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


class TestClose:
    """Tests for the ``issues close`` command."""

    def test_closes_correct_issues(
        self, with_student_repos, platform_url, issue
    ):
        # arrange
        open_issue = issue

        issue_to_close_title = "The title of an issue to close"
        issue_to_close_body = "The body of an issue to close"
        with tempfile.NamedTemporaryFile() as tmpfile:
            path = pathlib.Path(tmpfile.name)
            path.write_text(f"{issue_to_close_title}\n{issue_to_close_body}")
            issue_to_close = _TestIssue(
                issue_to_close_title, issue_to_close_body, path
            )

            for issue in [open_issue, issue_to_close]:
                funcs.run_repobee(
                    f"issues open "
                    f"--master-repo-names {const.TEMPLATE_REPOS_ARG} "
                    f"--base-url {platform_url} "
                    f"--issue {issue.path}"
                )

            # act
            funcs.run_repobee(
                [
                    *f"issues close --base-url {platform_url} "
                    f"--master-repo-names {const.TEMPLATE_REPOS_ARG} ".split(),
                    "--title-regex",
                    issue_to_close_title,
                ]
            )

        # assert
        iterations = 0
        for repo in funcs.get_repos(platform_url, const.TARGET_ORG_NAME):
            iterations += 1
            assert len(repo.issues) == 2
            first, second = repo.issues
            assert first.title == open_issue.title
            assert first.state == plug.IssueState.OPEN
            assert second.title == issue_to_close.title
            assert second.state == plug.IssueState.CLOSED

        assert iterations == len(const.STUDENT_TEAMS) * len(
            const.TEMPLATE_REPO_NAMES
        )
