import os
import pathlib
import re

import pytest

import repobee_plug as plug

import _repobee.ext
import _repobee.command.peer
import _repobee.ext.gitlab
import _repobee.cli.mainparser
import repobee_plug.cli

from _helpers.asserts import (
    assert_master_repos_exist,
    assert_repos_exist,
    assert_repos_contain,
    assert_on_groups,
    assert_issues_exist,
    assert_num_issues,
    assert_cloned_repos,
)
from _helpers.const import (
    VOLUME_DST,
    BASE_DOMAIN,
    LOCAL_DOMAIN,
    ORG_NAME,
    MASTER_ORG_NAME,
    MASTER_REPO_NAMES,
    STUDENT_TEAMS,
    STUDENT_TEAM_NAMES,
    STUDENT_REPO_NAMES,
    REPOBEE_GITLAB,
    BASE_ARGS_NO_TB,
    BASE_ARGS,
    STUDENTS_ARG,
    MASTER_REPOS_ARG,
    MASTER_ORG_ARG,
    TEACHER,
)
from _helpers.helpers import (
    api_instance,
    run_in_docker_with_coverage,
    run_in_docker,
    update_repo,
    hash_directory,
    expected_num_members_group_assertion,
)


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
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

    def test_clone_twice(self, with_student_repos, tmpdir, extra_args):
        """Cloning twice in a row should have the same effect as cloning once.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
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
        assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

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
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
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
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_cloned_repos(non_pre_existing_dirnames, tmpdir)
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
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *STUDENTS_ARG,
                "--discover-repos",
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestSetup:
    """Integration tests for the setup command."""

    def test_clean_setup(self, extra_args):
        """Test a first-time setup with master repos in the master org."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_on_groups(STUDENT_TEAMS)

    def test_setup_twice(self, extra_args):
        """Setting up twice should have the same effect as setting up once."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_on_groups(STUDENT_TEAMS)


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
                *repobee_plug.cli.CoreCommand.repos.update.as_name_tuple(),
                *MASTER_ORG_ARG,
                *BASE_ARGS,
                "--mn",
                master_repo,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_contain(STUDENT_TEAMS, [master_repo], filename, text)

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
                *repobee_plug.cli.CoreCommand.repos.update.as_name_tuple(),
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
        assert_repos_contain(STUDENT_TEAMS[1:], [master_repo], filename, text)
        assert_issues_exist(STUDENT_TEAMS[0:1], [master_repo], issue)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestMigrate:
    """Integration tests for the migrate command."""

    @pytest.fixture
    def local_master_repos(self, restore, extra_args):
        """Clone the master repos to disk. The restore fixture is explicitly
        included as it must be run before this fixture.
        """
        api = api_instance(MASTER_ORG_NAME)
        master_repo_urls = [
            url.replace(LOCAL_DOMAIN, BASE_DOMAIN)
            for url in api.get_repo_urls(MASTER_REPO_NAMES)
        ]
        # clone the master repos to disk first first
        git_commands = ["git clone {}".format(url) for url in master_repo_urls]
        result = run_in_docker(
            " && ".join(git_commands), extra_args=extra_args
        )

        assert result.returncode == 0
        return MASTER_REPO_NAMES

    def test_happy_path(self, local_master_repos, extra_args):
        """Migrate a few repos from the existing master repo into the target
        organization.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.repos.migrate.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_master_repos_exist(local_master_repos, ORG_NAME)


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
                *repobee_plug.cli.CoreCommand.issues.open.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-i",
                "{}/{}".format(VOLUME_DST, filename),
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_num_issues(STUDENT_TEAMS, MASTER_REPO_NAMES, 1)
        assert_issues_exist(STUDENT_TEAMS, MASTER_REPO_NAMES, self._ISSUE)


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
                *repobee_plug.cli.CoreCommand.issues.close.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-r",
                close_issue.title,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_issues_exist(
            STUDENT_TEAM_NAMES,
            MASTER_REPO_NAMES,
            close_issue,
            expected_state="closed",
        )
        assert_issues_exist(
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
            issue_pattern_template.format(repo_name, matched.title, TEACHER)
            for repo_name in repo_names
        ]
        unexpected_issue_output_patterns = [
            issue_pattern_template.format(repo_name, unmatched.title, TEACHER)
            for repo_name in repo_names
        ] + [
            r"\[ERROR\]"
        ]  # any kind of error is bad

        repo_arg = ["--discover-repos"] if discover_repos else MASTER_REPOS_ARG
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.issues.list.as_name_tuple(),
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
                *repobee_plug.cli.CoreCommand.reviews.assign.as_name_tuple(),
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
        assert_on_groups(
            expected_review_teams, single_group_assertion=group_assertion
        )
        assert_num_issues(STUDENT_TEAMS, [master_repo_name], 1)
        assert_issues_exist(
            STUDENT_TEAMS,
            [master_repo_name],
            _repobee.command.peer.DEFAULT_REVIEW_ISSUE,
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
                *repobee_plug.cli.CoreCommand.reviews.assign.as_name_tuple(),
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
        assert_num_issues(STUDENT_TEAMS, [master_repo_name], 0)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestEndReviews:
    def test_end_all_reviews(self, with_reviews, extra_args):
        master_repo_name, review_teams = with_reviews
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.reviews.end.as_name_tuple(),
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
        assert_on_groups(STUDENT_TEAMS)
        # review teams should not
        assert_on_groups(
            review_teams, all_groups_assertion=assert_no_actual_groups
        )

    def test_end_non_existing_reviews(self, with_reviews, extra_args):
        _, review_teams = with_reviews
        master_repo_name = MASTER_REPO_NAMES[0]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                *repobee_plug.cli.CoreCommand.reviews.end.as_name_tuple(),
                *BASE_ARGS,
                "--mn",
                master_repo_name,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_on_groups(STUDENT_TEAMS)
        assert_on_groups(
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
                *repobee_plug.cli.CoreCommand.reviews.check.as_name_tuple(),
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
                *repobee_plug.cli.CoreCommand.reviews.check.as_name_tuple(),
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
