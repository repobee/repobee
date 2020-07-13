"""Integration tests for the clone command."""

import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *

@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestClone:
    """Integration tests for the clone command."""

    def test_clean_clone(self, with_student_repos, tmpdir, extra_args):
        """Test cloning student repos when there are no repos in the current
        working directory.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

    def test_clone_twice(self, with_student_repos, tmpdir, extra_args):
        """Cloning twice in a row should have the same effect as cloning once.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        first_result = run_in_docker_with_coverage(
            command, extra_args=extra_args
        )
        second_result = run_in_docker_with_coverage(
            command, extra_args=extra_args
        )

        assert first_result.returncode == 0
        assert second_result.returncode == 0
        asserts.assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

    def test_clone_does_not_create_dirs_on_fail(
        self, with_student_repos, tmpdir, extra_args
    ):
        """Test that no local directories are created for repos that RepoBee
        fails to pull.
        """
        non_existing_master_repo_names = ["non-existing-1", "non-existing-2"]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLONE_PARSER,
                *BASE_ARGS,
                *STUDENTS_ARG,
                "--mn",
                " ".join(non_existing_master_repo_names),
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert [
            dir for dir in os.listdir(str(tmpdir)) if os.path.isdir(dir)
        ] == []

    def test_clone_does_not_alter_existing_dirs(
        self, with_student_repos, tmpdir, extra_args
    ):
        """Test that clone does not clobber existing directories."""
        team_with_local_repos = STUDENT_TEAMS[0]
        teams_without_local_repos = STUDENT_TEAMS[1:]
        pre_existing_dirnames = plug.generate_repo_names(
            [team_with_local_repos], MASTER_REPO_NAMES
        )
        non_pre_existing_dirnames = plug.generate_repo_names(
            teams_without_local_repos, MASTER_REPO_NAMES
        )

        expected_dir_hashes = dict()
        for dirname in pre_existing_dirnames:
            new_dir = tmpdir.mkdir(dirname)
            new_file = new_dir.join("file")
            new_file.write_text(dirname, encoding="utf-8")
            expected_dir_hashes[dirname] = hash_directory(new_dir)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_cloned_repos(non_pre_existing_dirnames, tmpdir)
        for dirname in pre_existing_dirnames:
            dirhash = hash_directory(pathlib.Path(str(tmpdir)) / dirname)
            assert dirhash == expected_dir_hashes[dirname], (
                "hash mismatch for " + dirname
            )

    def test_discover_repos(self, with_student_repos, tmpdir, extra_args):
        """Test that the --discover-repos option finds all student repos."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.CLONE_PARSER,
                *BASE_ARGS,
                *STUDENTS_ARG,
                "--discover-repos",
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)
