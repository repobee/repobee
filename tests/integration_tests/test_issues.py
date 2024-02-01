"""Tests for the issues category of commands."""

import pathlib
import tempfile
import collections
import itertools
import re

from typing import List, Tuple

import pytest

import repobee_plug as plug
from repobee_testhelpers import funcs
from repobee_testhelpers import const

import _repobee.hash

_TestIssue = collections.namedtuple("_TestIssue", "title body path")


class TestOpen:
    """Tests for the ``issues open`` command."""

    def test_open_issue_for_all_repos(
        self, with_student_repos, platform_url, issue
    ):
        expected_repo_names = plug.generate_repo_names(
            const.STUDENT_TEAMS, const.TEMPLATE_REPO_NAMES
        )

        funcs.run_repobee(
            f"issues open --assignments {const.TEMPLATE_REPOS_ARG} "
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

    def test_open_issues_from_double_blind_hook_results(
        self, with_student_repos, platform_url, tmp_path
    ):
        """Test opening issues from a hook results file gathered from listing
        issues from double-blind peer review.
        """

        # arrange
        results_file = tmp_path / "hf.json"
        key = "1234"
        assignment = const.TEMPLATE_REPO_NAMES[0]
        review_title = "This is the peer review"
        _setup_double_blind_reviews_with_review_issues(
            assignment, key, platform_url, review_title
        )
        funcs.run_repobee(
            f"issues list --assignments {assignment} "
            f"--double-blind-key {key} "
            f"--base-url {platform_url} "
            f"--hook-results-file {results_file}"
        )

        # act
        funcs.run_repobee(
            f"issues open --assignments {assignment} "
            f"--base-url {platform_url} "
            f"--hook-results-file {results_file}"
        )

        # assert
        expected_repo_names = set(
            plug.generate_repo_names(
                [t.name for t in const.STUDENT_TEAMS], [assignment]
            )
        )
        repos = [
            repo
            for repo in funcs.get_repos(platform_url)
            if repo.name in expected_repo_names
        ]
        assert repos
        for repo in repos:
            assert len(repo.issues) == 2
            assert review_title in [i.title for i in repo.issues]


class TestClose:
    """Tests for the ``issues close`` command."""

    def test_closes_correct_issues(self, with_student_repos, platform_url):
        issue_to_close, open_issue = _open_predefined_issues(platform_url)

        funcs.run_repobee(
            [
                *f"issues close --base-url {platform_url} "
                f"--assignments {const.TEMPLATE_REPOS_ARG} ".split(),
                "--title-regex",
                issue_to_close.title,
            ]
        )

        iterations = 0
        for repo in funcs.get_repos(platform_url, const.TARGET_ORG_NAME):
            iterations += 1
            assert len(repo.issues) == 2
            actual_open_issue, *_ = [
                i for i in repo.issues if i.state == plug.IssueState.OPEN
            ]
            actual_closed_issue, *_ = [
                i for i in repo.issues if i.state == plug.IssueState.CLOSED
            ]
            assert actual_open_issue.title == open_issue.title
            assert actual_closed_issue.title == issue_to_close.title

        assert iterations == len(const.STUDENT_TEAMS) * len(
            const.TEMPLATE_REPO_NAMES
        )


class TestList:
    """Tests for the ``issues list`` command."""

    def test_lists_open_issues_by_default(
        self, platform_url, with_student_repos, capsys
    ):
        criteria_issue, notice_issue = _open_predefined_issues(platform_url)

        funcs.run_repobee(
            f"issues list -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}"
        )

        stdout = capsys.readouterr().out
        for student_team, test_issue in itertools.product(
            const.STUDENT_TEAMS, [criteria_issue, notice_issue]
        ):
            assert re.search(
                rf"{student_team.name}.*{test_issue.title}", stdout
            )

    def test_show_body(self, platform_url, with_student_repos, capsys):
        issues = _open_predefined_issues(platform_url)

        funcs.run_repobee(
            f"issues list -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            "--show-body"
        )

        stdout = capsys.readouterr().out
        expected_num_bodies = len(const.STUDENT_TEAMS) * len(
            const.TEMPLATE_REPO_NAMES
        )
        for issue in issues:
            assert len(re.findall(issue.body, stdout)) == expected_num_bodies

    def test_list_double_blind_issues(
        self, platform_url, with_student_repos, capsys
    ):
        key = "1234"
        assignment = const.TEMPLATE_REPO_NAMES[0]
        review_title = "This is the peer review"
        _setup_double_blind_reviews_with_review_issues(
            assignment, key, platform_url, review_title
        )

        funcs.run_repobee(
            f"issues list --assignments {assignment} "
            f"--double-blind-key {key} "
            f"--base-url {platform_url}"
        )

        stdout = capsys.readouterr().out
        expected_repo_names = plug.generate_repo_names(
            const.STUDENT_TEAMS, [assignment]
        )
        for repo_name in expected_repo_names:
            assert re.search(rf"{repo_name}.*{review_title}", stdout)


def _get_anonymous_review_team(
    student_team: plug.StudentTeam,
    assignment: str,
    key: str,
    api: plug.PlatformAPI,
) -> plug.Team:
    review_team, *_ = list(
        api.get_teams([_repobee.hash.keyed_hash(student_team.name, key, 20)])
    )
    return review_team


def _setup_double_blind_reviews_with_review_issues(
    assignment: str, key: str, platform_url: str, review_title: str
) -> None:
    funcs.run_repobee(
        f"reviews assign --double-blind-key {key} "
        f"--assignments {assignment} "
        f"--base-url {platform_url}"
    )
    api = funcs.get_api(platform_url)

    for team in const.STUDENT_TEAMS:
        review_team = _get_anonymous_review_team(team, assignment, key, api)

        student = review_team.members[0]
        anon_repo = next(api.get_team_repos(review_team))
        issue = api.create_issue(
            review_title, "This is an excellent review", anon_repo
        )
        issue.implementation.author = student


@pytest.fixture
def issue():
    title = "This is the title"
    body = "And this\nis the body."
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "issue.md"
        path.write_text(f"{title}\n{body}")
        yield _TestIssue(title, body, path)


def _open_predefined_issues(
    platform_url: str,
) -> Tuple[_TestIssue, _TestIssue]:
    """Open two pre-defined issues in all student repos. Note that this only
    works if the student repos actually exist before invoking this function.

    IMPORTANT: The paths are actually invalid, the directory is deleted before
    the function returns.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        issues_dir = pathlib.Path(tmpdir)
        criteria_issue = _TestIssue(
            title="Grading criteria",
            body="You must do very well!",
            path=issues_dir / "grading.md",
        )
        notice_issue = _TestIssue(
            title="Important notice",
            body="The grading criteria is fake!",
            path=issues_dir / "notice.md",
        )
        _open_issues_in_student_repos(
            [criteria_issue, notice_issue], platform_url
        )

    return criteria_issue, notice_issue


def _open_issues_in_student_repos(
    test_issues: List[_TestIssue], platform_url: str
):
    """Open issues on the platform in all student repos."""
    for issue in test_issues:
        issue.path.parent.mkdir(parents=True, exist_ok=True)
        issue.path.write_text(f"{issue.title}\n{issue.body}", encoding="utf8")
        funcs.run_repobee(
            f"issues open "
            f"--assignments {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            f"--issue {issue.path}",
            workdir=issue.path.parent,
        )
