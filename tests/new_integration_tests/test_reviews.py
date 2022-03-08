"""Tests for the reviews category of commands."""
import re
import os

import pytest
import packaging.version


import repobee_plug as plug

from repobee_testhelpers import funcs
from repobee_testhelpers import const

import _repobee.constants
from _repobee import featflags


class TestAssign:
    """Tests for the ``reviews assign`` command."""

    def test_assign_single_review_creates_review_teams(
        self, platform_dir, platform_url, with_student_repos
    ):
        expected_review_team_names = {
            plug.generate_review_team_name(team, template_repo_name)
            for team in const.STUDENT_TEAMS
            for template_repo_name in const.TEMPLATE_REPO_NAMES
        }

        funcs.run_repobee(
            f"reviews assign -n 1 --base-url {platform_url} "
            f"--assignments {const.TEMPLATE_REPOS_ARG}"
        )

        review_teams = [
            team
            for team in funcs.get_teams(platform_url, const.TARGET_ORG_NAME)
            if team.name in expected_review_team_names
        ]

        assert {t.name for t in review_teams} == expected_review_team_names
        assert all(map(lambda t: len(t.members) == 1, review_teams))

    def test_assign_single_review_creates_review_issues(
        self, platform_dir, platform_url, with_student_repos
    ):
        expected_review_issue_titles = {
            f"Peer review ({team})"
            for team in const.STUDENT_TEAMS
            for template_repo_name in const.TEMPLATE_REPO_NAMES
        }

        funcs.run_repobee(
            f"reviews assign -n 1 --base-url {platform_url} "
            f"--assignments {const.TEMPLATE_REPOS_ARG}"
        )

        review_issues = [
            issue
            for issue in funcs.get_issues(platform_url, const.TARGET_ORG_NAME)
            if issue.title in expected_review_issue_titles
        ]

        assert {t.title for t in review_issues} == expected_review_issue_titles
        assert all(
            map(lambda t: len(t.implementation.assignees) == 1, review_issues)
        )

    def test_double_blind_creates_correct_amount_of_anonymous_copies(
        self, platform_url, with_student_repos
    ):
        assignment_name = const.TEMPLATE_REPO_NAMES[0]
        api = funcs.get_api(platform_url)
        num_repos_before = len(list(api.get_repos()))

        funcs.run_repobee(
            f"reviews assign --num-reviews 1 "
            f"--base-url {platform_url} "
            f"--double-blind-key 1234 "
            f"--assignments {assignment_name}"
        )

        api._restore_platform_state()
        num_repos_after = len(list(api.get_repos()))
        assert num_repos_after == num_repos_before + len(const.STUDENT_TEAMS)


class TestEnd:
    """Tests for the ``reviews end`` command."""

    def test_end(self, platform_dir, platform_url, with_student_repos):
        review_team_names = {
            plug.generate_review_team_name(team, template_repo_name)
            for team in const.STUDENT_TEAMS
            for template_repo_name in const.TEMPLATE_REPO_NAMES
        }
        funcs.run_repobee(
            f"reviews assign -n 1 --base-url {platform_url} "
            f"--assignments {const.TEMPLATE_REPOS_ARG}"
        )

        funcs.run_repobee(
            f"reviews end --base-url {platform_url} "
            f"--assignments {const.TEMPLATE_REPOS_ARG}"
        )

        platform_teams = funcs.get_teams(platform_url, const.TARGET_ORG_NAME)
        review_teams = [
            team for team in platform_teams if team.name in review_team_names
        ]

        assert not review_teams
        assert len(platform_teams) == len(const.STUDENT_TEAMS)

    def test_end_double_blind_reviews_when_review_teams_are_missing(
        self, platform_url, with_student_repos
    ):
        """Even if the review teams are missing, the anonymous repos should be
        deleted when running end. Such cases can occurr when there is failure
        in setup, see issue #825 for details.
        """
        # arrange
        assignment_name = const.TEMPLATE_REPO_NAMES[0]
        api = funcs.get_api(platform_url)
        num_repos_before = len(list(api.get_repos()))
        key = 1234

        funcs.run_repobee(
            f"reviews assign --num-reviews 1 "
            f"--base-url {platform_url} "
            f"--double-blind-key {key} "
            f"--assignments {assignment_name}"
        )

        api._restore_platform_state()
        review_teams = [
            team for team in api.get_teams() if "-" not in team.name
        ]
        for team in review_teams:
            api.delete_team(team)

        # act
        funcs.run_repobee(
            f"reviews end "
            f"--base-url {platform_url} "
            f"--double-blind-key {key} "
            f"--assignments {assignment_name}"
        )

        # assert
        api._restore_platform_state()
        num_repos_after = len(list(api.get_repos()))
        assert num_repos_after == num_repos_before

    def test_end_with_allocations_file(
        self,
        platform_url,
        with_student_repos,
        tmp_path,
        activate_review_command_preview,
    ):
        """Test the RepoBee 4 version of `reviews end`, that just takes an
        allocations file.
        """
        # arrange
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=False)
        alloc_file = workdir / "review_allocations.json"

        funcs.run_repobee(
            f"{plug.cli.CoreCommand.reviews.assign} "
            f"--base-url {platform_url} "
            f"-n 1 "
            f"--assignments {const.TEMPLATE_REPOS_ARG}",
            workdir=workdir,
        )

        # act
        funcs.run_repobee(
            f"{plug.cli.CoreCommand.reviews.end} --base-url {platform_url} "
            f"--allocations-file {alloc_file}",
            workdir=workdir,
        )

        # assert
        api = funcs.get_api(platform_url)
        review_team_names = {
            plug.generate_review_team_name(team, template_repo_name)
            for team in const.STUDENT_TEAMS
            for template_repo_name in const.TEMPLATE_REPO_NAMES
        }

        existing_team_names = {team.name for team in api.get_teams()}
        assert not existing_team_names.intersection(review_team_names)


class TestCheck:
    """Tests for the ``reviews check`` command."""

    def test_check(
        self, platform_dir, platform_url, with_student_repos, capsys
    ):
        template_repo_name = const.TEMPLATE_REPO_NAMES[0]
        funcs.run_repobee(
            f"reviews assign -n 1 --base-url {platform_url} "
            f"--assignments {template_repo_name}"
        )

        funcs.run_repobee(
            [
                *f"reviews check -n 1 --base-url {platform_url} "
                f"--assignments {const.TEMPLATE_REPOS_ARG} ".split(),
                "--title-regex",
                "Peer review",
            ]
        )

        stdout = capsys.readouterr().out
        for team in const.STUDENT_TEAMS:
            assert re.search(fr"{team.name}\s+0\s+1", stdout)

    def test_check_with_allocations_file(
        self,
        platform_dir,
        platform_url,
        with_student_repos,
        capsys,
        activate_review_command_preview,
        tmp_path,
    ):
        """Test the RepoBee 4 preview version of `reviews check`."""
        # arrange
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=False)
        alloc_file = workdir / "review_allocations.json"

        funcs.run_repobee(
            f"{plug.cli.CoreCommand.reviews.assign} "
            f"--base-url {platform_url} "
            "-n 1 "
            f"--assignments {const.TEMPLATE_REPO_NAMES[0]}",
            workdir=workdir,
        )

        # act
        funcs.run_repobee(
            f"{plug.cli.CoreCommand.reviews.check} "
            f"--base-url {platform_url} "
            f"--allocations-file {alloc_file} "
            "--title-regex 'Peer review'",
            workdir=workdir,
        )

        # assert
        stdout = capsys.readouterr().out
        for team in const.STUDENT_TEAMS:
            assert re.search(fr"{team.name}\s+0\s+1", stdout)


@pytest.fixture
def activate_review_command_preview():
    if packaging.version.Version(
        _repobee.__version__
    ) >= packaging.version.Version("4.0.0"):
        raise RuntimeError(
            "Peer review command preview feature should be removed!"
        )
    os.environ[
        featflags.FeatureFlag.REPOBEE_4_REVIEW_COMMANDS.value
    ] = featflags.FEATURE_ENABLED_VALUE
    yield
    del os.environ[featflags.FeatureFlag.REPOBEE_4_REVIEW_COMMANDS.value]
