"""Tests for the reviews category of commands."""
import re

import repobee_plug as plug

from repobee_testhelpers import funcs
from repobee_testhelpers import const


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
            f"--master-repo-names {const.TEMPLATE_REPOS_ARG}",
        )

        review_teams = [
            team
            for team in funcs.get_teams(platform_url, const.TARGET_ORG_NAME)
            if team.name in expected_review_team_names
        ]

        assert {t.name for t in review_teams} == expected_review_team_names
        assert all(map(lambda t: len(t.members) == 1, review_teams))


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
            f"--master-repo-names {const.TEMPLATE_REPOS_ARG}",
        )

        funcs.run_repobee(
            f"reviews end --base-url {platform_url} "
            f"--master-repo-names {const.TEMPLATE_REPOS_ARG}"
        )

        platform_teams = funcs.get_teams(platform_url, const.TARGET_ORG_NAME)
        review_teams = [
            team for team in platform_teams if team.name in review_team_names
        ]

        assert not review_teams
        assert len(platform_teams) == len(const.STUDENT_TEAMS)


class TestCheck:
    """Tests for the ``reviews check`` command."""

    def test_check(
        self, platform_dir, platform_url, with_student_repos, capsys
    ):
        template_repo_name = const.TEMPLATE_REPO_NAMES[0]
        funcs.run_repobee(
            f"reviews assign -n 1 --base-url {platform_url} "
            f"--master-repo-names {template_repo_name}",
        )

        funcs.run_repobee(
            [
                *f"reviews check -n 1 --base-url {platform_url} "
                f"--master-repo-names {const.TEMPLATE_REPOS_ARG} ".split(),
                "--title-regex",
                "Peer review",
            ]
        )

        stdout = capsys.readouterr().out
        for team in const.STUDENT_TEAMS:
            assert re.search(fr"{team.name}\s+0\s+1", stdout)
