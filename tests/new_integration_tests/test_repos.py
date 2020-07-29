"""Tests for the repos category of commands."""
import pathlib
import tempfile

from typing import List

import repobee_plug as plug
from repobee_plug.testhelpers import funcs


from repobee_plug.testhelpers.const import (
    STUDENTS_FILE,
    STUDENT_TEAMS,
    TARGET_ORG_NAME,
    TEACHER,
    TEMPLATE_ORG_NAME,
    TEMPLATE_REPO_NAMES,
    TEMPLATE_REPOS_ARG,
)


def assert_student_repos_match_templates(
    student_teams: List[plug.Team],
    template_repo_names: List[str],
    student_repo_dir: pathlib.Path,
):
    """Assert that the content of the student repos matches the content of the
    respective template repos.
    """
    expected_repo_asserts = len(student_teams) * len(template_repo_names)
    actual_repo_asserts = 0

    for template_name in template_repo_names:
        student_repos = [
            student_repo_dir / repo_name
            for repo_name in plug.generate_repo_names(
                student_teams, [template_name]
            )
        ]
        assert len(student_repos) == len(student_teams)
        template_repo_hashes = funcs.template_repo_hashes()
        for repo in student_repos:
            actual_repo_asserts += 1
            assert funcs.tree_hash(repo) == template_repo_hashes[template_name]

    assert (
        expected_repo_asserts == actual_repo_asserts
    ), "Performed fewer asserts than expected"


class TestSetup:
    """Tests for the ``repos setup`` command."""

    def test_setup_single_template_repo(self, platform_dir, platform_url):
        template_repo_name = TEMPLATE_REPO_NAMES[0]
        funcs.run_repobee(
            f"repos setup --mn {template_repo_name} "
            f"--students-file {STUDENTS_FILE} "
            f"--base-url {platform_url} "
            f"--user {TEACHER} "
            f"--org-name {TARGET_ORG_NAME} "
            f"--master-org-name {TEMPLATE_ORG_NAME}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, [template_repo_name], platform_dir / TARGET_ORG_NAME
        )

    def test_setup_multiple_template_repos(self, platform_dir, platform_url):
        funcs.run_repobee(
            f"repos setup --mn {TEMPLATE_REPOS_ARG} "
            f"--students-file {STUDENTS_FILE} "
            f"--base-url {platform_url} "
            f"--user {TEACHER} "
            f"--org-name {TARGET_ORG_NAME} "
            f"--master-org-name {TEMPLATE_ORG_NAME}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, platform_dir / TARGET_ORG_NAME
        )

    def test_setup_multiple_template_repos_twice(
        self, platform_dir, platform_url
    ):
        """Running setup command twice should have the same effect as running
        it once.
        """
        for _ in range(2):
            funcs.run_repobee(
                f"repos setup --mn {TEMPLATE_REPOS_ARG} "
                f"--students-file {STUDENTS_FILE} "
                f"--base-url {platform_url} "
                f"--user {TEACHER} "
                f"--org-name {TARGET_ORG_NAME} "
                f"--master-org-name {TEMPLATE_ORG_NAME}"
            )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, platform_dir / TARGET_ORG_NAME
        )


class TestClone:
    """Tests for the ``repos clone`` command."""

    def test_clone_all_repos(self, platform_url, with_student_repos):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = pathlib.Path(tmp)
            funcs.run_repobee(
                f"repos clone --mn {TEMPLATE_REPOS_ARG} "
                f"--students-file {STUDENTS_FILE} "
                f"--base-url {platform_url} "
                f"--user {TEACHER} "
                f"--org-name {TARGET_ORG_NAME} ",
                workdir=workdir,
            )
            assert_student_repos_match_templates(
                STUDENT_TEAMS, TEMPLATE_REPO_NAMES, workdir
            )
