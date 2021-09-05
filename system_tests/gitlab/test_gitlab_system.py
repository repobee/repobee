import os
import pathlib
import re
import subprocess
import contextlib
import io
import shlex

import pytest
import gitlab

import repobee_plug as plug
import repobee_testhelpers

from repobee_testhelpers.funcs import hash_directory, run_repobee

import _repobee.ext
import _repobee.command.peer
import _repobee.ext.gitlab
import _repobee.cli.mainparser
import repobee_plug.cli

from _helpers.asserts import (
    assert_template_repos_exist,
    assert_repos_exist,
    assert_repos_contain,
    assert_on_groups,
    assert_issues_exist,
    assert_num_issues,
    assert_cloned_repos,
)
from _helpers.const import (
    TEMPLATE_ORG_NAME,
    ORG_NAME,
    assignment_names,
    STUDENT_TEAMS,
    STUDENT_TEAM_NAMES,
    BASE_ARGS_NO_TB,
    BASE_ARGS,
    STUDENTS_ARG,
    MASTER_REPOS_ARG,
    TEMPLATE_ORG_ARG,
    TEACHER,
    ADMIN_TOKEN,
    BASE_URL,
)
from _helpers.helpers import (
    api_instance,
    update_repo,
    expected_num_members_group_assertion,
    gitlab_and_groups,
)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestClone:
    """Integration tests for the clone command."""

    def test_clean_clone(self, with_student_repos, tmpdir):
        """Test cloning student repos when there are no repos in the current
        working directory.
        """
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_cloned_repos(STUDENT_TEAMS, assignment_names, tmpdir)

    def test_clone_twice(self, with_student_repos, tmpdir):
        """Cloning twice in a row should have the same effect as cloning
        once.
        """
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_cloned_repos(STUDENT_TEAMS, assignment_names, tmpdir)

    def test_clone_does_not_create_dirs_on_fail(
        self, with_student_repos, tmpdir
    ):
        """Test that no local directories are created for repos that RepoBee
        fails to pull.
        """
        non_existing_assignment_names = ["non-existing-1", "non-existing-2"]
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *STUDENTS_ARG,
                "-a",
                " ".join(non_existing_assignment_names),
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert [
            dir for dir in os.listdir(str(tmpdir)) if os.path.isdir(dir)
        ] == []

    def test_clone_does_not_alter_existing_dirs(
        self, with_student_repos, tmpdir
    ):
        """Test that clone does not clobber existing directories."""
        team_with_local_repos = STUDENT_TEAMS[0]
        teams_without_local_repos = STUDENT_TEAMS[1:]

        expected_dir_hashes = []
        for template_repo_name in assignment_names:
            new_dir = plug.fileutils.generate_repo_path(
                str(tmpdir), team_with_local_repos.name, template_repo_name
            )
            new_dir.mkdir(parents=True)
            new_file = new_dir / "file"
            new_file.write_text(str(new_dir), encoding="utf-8")
            expected_dir_hashes.append((new_dir, hash_directory(new_dir)))
            repobee_testhelpers.funcs.initialize_repo(new_dir)

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_cloned_repos(
            teams_without_local_repos, assignment_names, tmpdir
        )
        for dirpath, expected_hash in expected_dir_hashes:
            dirhash = hash_directory(dirpath)
            assert dirhash == expected_hash, "hash mismatch for " + dirpath

    def test_discover_repos(self, with_student_repos, tmpdir):
        """Test that the --discover-repos option finds all student repos."""
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.clone.as_name_tuple(),
                *BASE_ARGS,
                *STUDENTS_ARG,
                "--discover-repos",
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_cloned_repos(STUDENT_TEAMS, assignment_names, tmpdir)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestSetup:
    """Integration tests for the setup command."""

    def test_clean_setup(self, tmpdir):
        """Test a first-time setup with master repos in the master org."""
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        assert_repos_exist(STUDENT_TEAMS, assignment_names)
        assert_on_groups(STUDENT_TEAMS)

    def test_clean_setup_in_subgroup(self, tmpdir):
        """It should be possible to use a subgroup as the target org."""
        gl, template_group, target_group = gitlab_and_groups()
        subgroup_name = "bestgroup"
        subgroup_full_path = f"{target_group.path}/{subgroup_name}"
        gl.groups.create(
            dict(
                name=subgroup_name,
                path=subgroup_name,
                parent_id=target_group.id,
            )
        )

        base_args = [
            arg if arg != ORG_NAME else subgroup_full_path for arg in BASE_ARGS
        ]

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *base_args,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        assert_repos_exist(
            STUDENT_TEAMS, assignment_names, org_name=subgroup_full_path
        )

    def test_setup_twice(self, tmpdir):
        """Setting up twice should have the same effect as setting up once."""
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        assert_repos_exist(STUDENT_TEAMS, assignment_names)
        assert_on_groups(STUDENT_TEAMS)

    def test_setup_with_token_owner_as_student(self, tmpdir):
        """Setting up with the token owner as a student should not cause
        a crash (see #812)
        """
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                "--students",
                TEACHER,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        assert_repos_exist(
            [plug.StudentTeam(members=[TEACHER])], assignment_names
        )

    def test_setup_with_default_branch_protection_does_not_carry_over(
        self, tmpdir
    ):
        """Student repositories created when global default branch
        protection is enabled on the GitLab instance, should still not have
        default branch protection.
        """
        # arrange
        gl = gitlab.Gitlab(
            url=BASE_URL, private_token=ADMIN_TOKEN, ssl_verify=False
        )
        gl.auth()
        settings = gl.settings.get()
        settings.default_branch_protection = (
            _repobee.ext.gitlab.DefaultBranchProtection.FULL.value
        )
        settings.save()
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        # act
        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        # assert
        api = api_instance(ORG_NAME)
        loop_ran = False
        for repo in api.get_repos():
            loop_ran = True
            assert not repo.implementation.protectedbranches.list()

        assert loop_ran, "assertion loop did not execute"

    def test_setup_with_twice_with_wrong_case_on_second_setup(self, tmpdir):
        """User names on GitLab are case insensitive, and so setting up repos
        for the same student with two different cases of characters should work
        the same as setting up just once

        See
        https://github.com/repobee/repobee/issues/900#issuecomment-830075510
        for a bug where this was not the case.
        """
        student = STUDENT_TEAMS[0].members[0]
        student_lowercase = STUDENT_TEAMS[0].members[0].lower()
        # the original should be lowercase
        assert (
            student == student_lowercase
        ), "expected real student username to be lowercase"

        student_uppercase = student_lowercase.upper()
        base_command = [
            *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
            *BASE_ARGS,
            *TEMPLATE_ORG_ARG,
            *MASTER_REPOS_ARG,
            "--students",
        ]

        def _cmd(student):
            return " ".join(base_command + [student])

        run_repobee(
            _cmd(student_lowercase),
            workdir=tmpdir,
            plugins=[_repobee.ext.gitlab],
        )
        run_repobee(
            _cmd(student_uppercase),
            workdir=tmpdir,
            plugins=[_repobee.ext.gitlab],
        )

        assert_repos_exist(
            [plug.StudentTeam(members=[student])], assignment_names
        )

    def test_setup_with_wrong_case_on_student(self, tmpdir):
        """User names are case insensitive on GitLab, and so setup should work
        fine even if the case of some character in a student's username is
        "incorrect".

        See https://github.com/repobee/repobee/issues/900
        """
        student = STUDENT_TEAMS[0].members[0]
        student_wrong_case = student.upper()
        assert (
            student != student_wrong_case
        ), "cases match, test is pointless :("

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                *BASE_ARGS,
                *TEMPLATE_ORG_ARG,
                *MASTER_REPOS_ARG,
                "--students",
                student_wrong_case,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_repos_exist(
            [plug.StudentTeam(members=[student])], assignment_names
        )


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestUpdate:
    """Integration tests for the update command."""

    def test_happy_path(self, with_student_repos, tmpdir):
        master_repo = assignment_names[0]
        filename = "superfile.super"
        text = "some epic content\nfor this file!"
        update_repo(master_repo, filename, text)

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.update.as_name_tuple(),
                *TEMPLATE_ORG_ARG,
                *BASE_ARGS,
                "-a",
                master_repo,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])
        assert_repos_contain(STUDENT_TEAMS, [master_repo], filename, text)

    def test_opens_issue_if_update_rejected(self, tmpdir, with_student_repos):
        master_repo = assignment_names[0]
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
                *repobee_plug.cli.CoreCommand.repos.update.as_name_tuple(),
                *TEMPLATE_ORG_ARG,
                *BASE_ARGS,
                "-a",
                master_repo,
                *STUDENTS_ARG,
                "--issue",
                issue_file.name,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_repos_contain(STUDENT_TEAMS[1:], [master_repo], filename, text)
        assert_issues_exist(STUDENT_TEAMS[0:1], [master_repo], issue)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestMigrate:
    """Integration tests for the migrate command."""

    @pytest.fixture
    def local_master_repos(self, restore, tmpdir):
        """Clone the master repos to disk. The restore fixture is explicitly
        included as it must be run before this fixture.
        """
        api = api_instance(TEMPLATE_ORG_NAME)
        template_repo_urls = [
            api.insert_auth(url) for url in api.get_repo_urls(assignment_names)
        ]
        # clone the master repos to disk first first
        git_commands = [
            "git clone {}".format(url) for url in template_repo_urls
        ]

        for cmd in git_commands:
            subprocess.run(shlex.split(cmd), check=True, cwd=str(tmpdir))

        return assignment_names

    def test_happy_path(self, local_master_repos, tmpdir):
        """Migrate a few repos from the existing master repo into the target
        organization.
        """
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.repos.migrate.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                "--allow-local-templates",
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_template_repos_exist(local_master_repos, ORG_NAME)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestOpenIssues:
    """Tests for the open-issues command."""

    _ISSUE = plug.Issue(title="This is a title", body="This is a body")

    def test_happy_path(self, tmpdir):
        """Test opening an issue in each student repo."""
        filename = "issue.md"
        text = "{}\n{}".format(self._ISSUE.title, self._ISSUE.body)
        tmpdir.join(filename).write_text(text, encoding="utf-8")

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.issues.open.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-i",
                f"{tmpdir}/{filename}",
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_num_issues(STUDENT_TEAMS, assignment_names, 1)
        assert_issues_exist(STUDENT_TEAMS, assignment_names, self._ISSUE)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestCloseIssues:
    """Tests for the close-issues command."""

    def test_closes_only_matched_issues(self, open_issues, tmpdir):
        """Test that close-issues respects the regex."""
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        close_issue = open_issues[0]
        open_issue = open_issues[1]
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.issues.close.as_name_tuple(),
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-r",
                close_issue.title,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_issues_exist(
            STUDENT_TEAM_NAMES,
            assignment_names,
            close_issue,
            expected_state="closed",
        )
        assert_issues_exist(
            STUDENT_TEAM_NAMES,
            assignment_names,
            open_issue,
            expected_state="opened",
        )


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestListIssues:
    """Tests for the list-issues command."""

    @pytest.mark.parametrize("discover_repos", [False, True])
    def test_lists_matching_issues(self, open_issues, tmpdir, discover_repos):
        # arrange
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        matched = open_issues[0]
        unmatched = open_issues[1]
        repo_names = plug.generate_repo_names(STUDENT_TEAMS, assignment_names)

        issue_pattern_template = r"^.*{}/#\d:\s+{}.*by {}.?$"
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
                *repobee_plug.cli.CoreCommand.issues.list.as_name_tuple(),
                *BASE_ARGS,
                *repo_arg,
                *STUDENTS_ARG,
                "-r",
                matched.title,
            ]
        )

        # act
        with contextlib.redirect_stdout(io.StringIO()) as sio:
            run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        output = sio.getvalue()

        # assert
        search_flags = re.MULTILINE
        for expected_pattern in expected_issue_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_issue_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestAssignReviews:
    """Tests for the assign-reviews command."""

    def test_assign_one_review(self, with_student_repos, tmpdir):
        assignment_name = assignment_names[1]
        expected_review_teams = [
            plug.StudentTeam(
                members=[],
                name=plug.generate_review_team_name(
                    student_team_name, assignment_name
                ),
            )
            for student_team_name in STUDENT_TEAM_NAMES
        ]
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.reviews.assign.as_name_tuple(),
                *BASE_ARGS,
                "-a",
                assignment_name,
                *STUDENTS_ARG,
                "-n",
                "1",
            ]
        )
        group_assertion = expected_num_members_group_assertion(
            expected_num_members=1
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_on_groups(
            expected_review_teams, single_group_assertion=group_assertion
        )
        assert_num_issues(STUDENT_TEAMS, [assignment_name], 1)
        assert_issues_exist(
            STUDENT_TEAMS,
            [assignment_name],
            _repobee.command.peer.DEFAULT_REVIEW_ISSUE,
            expected_num_asignees=1,
        )

    def test_assign_to_nonexisting_students(self, with_student_repos, tmpdir):
        """If you try to assign reviews where one or more of the allocated
        student repos don't exist, there should be an error.
        """
        assignment_name = assignment_names[1]
        non_existing_group = "non-existing-group"
        student_team_names = STUDENT_TEAM_NAMES + [non_existing_group]

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.reviews.assign.as_name_tuple(),
                *BASE_ARGS_NO_TB,
                "-a",
                assignment_name,
                "-s",
                *student_team_names,
                "-n",
                "1",
            ]
        )

        with contextlib.redirect_stdout(io.StringIO()) as sio:
            run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        output = sio.getvalue()

        assert (
            "[ERROR] NotFoundError: Can't find repos: {}".format(
                plug.generate_repo_name(non_existing_group, assignment_name)
            )
            in output
        )
        assert_num_issues(STUDENT_TEAMS, [assignment_name], 0)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestEndReviews:
    def test_end_all_reviews(self, with_reviews, tmpdir):
        assignment_name, review_teams = with_reviews
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.reviews.end.as_name_tuple(),
                *BASE_ARGS,
                "-a",
                assignment_name,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        def assert_no_actual_groups(expected, actual):
            assert not actual

        # student teams should still exist
        assert_on_groups(STUDENT_TEAMS)
        # review teams should not
        assert_on_groups(
            review_teams, all_groups_assertion=assert_no_actual_groups
        )

    def test_end_non_existing_reviews(self, with_reviews, tmpdir):
        _, review_teams = with_reviews
        assignment_name = assignment_names[0]
        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.reviews.end.as_name_tuple(),
                *BASE_ARGS,
                "-a",
                assignment_name,
                *STUDENTS_ARG,
            ]
        )

        run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        assert_on_groups(STUDENT_TEAMS)
        assert_on_groups(
            review_teams,
            single_group_assertion=expected_num_members_group_assertion(1),
        )


class TestCheckReviews:
    """Tests for check-reviews command."""

    def test_no_reviews_opened(self, with_reviews, tmpdir):
        assignment_name, _ = with_reviews
        num_reviews = 0
        num_expected_reviews = 1
        assignment_name = assignment_names[1]
        pattern_template = r"{}.*{}.*{}.*\w+-{}.*"
        expected_output_patterns = [
            pattern_template.format(
                team_name,
                str(num_reviews),
                str(num_expected_reviews - num_reviews),
                assignment_name,
            )
            for team_name in STUDENT_TEAM_NAMES
        ]
        unexpected_output_patterns = [r"\[ERROR\]"]

        command = " ".join(
            [
                *repobee_plug.cli.CoreCommand.reviews.check.as_name_tuple(),
                *BASE_ARGS,
                "-a",
                assignment_name,
                *STUDENTS_ARG,
                "--num-reviews",
                str(num_expected_reviews),
                "--title-regex",
                "Review",
            ]
        )

        with contextlib.redirect_stdout(io.StringIO()) as sio:
            run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        output = sio.getvalue()

        search_flags = re.MULTILINE
        for expected_pattern in expected_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)

    def test_expect_too_many_reviews(self, with_reviews, tmpdir):
        """Test that warnings are printed if a student is assigned to fewer
        review teams than expected.
        """
        assignment_name, _ = with_reviews
        num_reviews = 0
        actual_assigned_reviews = 1
        num_expected_reviews = 2
        assignment_name = assignment_names[1]
        warning_template = (
            r"\[WARNING\] Expected {} to be assigned to {} review teams, but "
            "found {}. Review teams may have been tampered with."
        )
        pattern_template = r"{}.*{}.*{}.*\w+-{}.*"
        expected_output_patterns = [
            pattern_template.format(
                team_name,
                str(num_reviews),
                str(actual_assigned_reviews - num_reviews),
                assignment_name,
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
                *repobee_plug.cli.CoreCommand.reviews.check.as_name_tuple(),
                *BASE_ARGS,
                "-a",
                assignment_name,
                *STUDENTS_ARG,
                "--num-reviews",
                str(num_expected_reviews),
                "--title-regex",
                "Review",
            ]
        )

        with contextlib.redirect_stdout(io.StringIO()) as sio:
            run_repobee(command, workdir=tmpdir, plugins=[_repobee.ext.gitlab])

        output = sio.getvalue()

        search_flags = re.MULTILINE
        for expected_pattern in expected_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)
