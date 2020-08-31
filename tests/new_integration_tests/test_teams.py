"""Tests for the teams category of commands."""

from repobee_testhelpers import funcs
from repobee_testhelpers import const


class TestCreate:
    """Tests for ``teams create``."""

    def test_run_when_no_teams_exist(self, platform_url):
        funcs.run_repobee(f"teams create --base-url {platform_url}")
        assert sorted(funcs.get_student_teams(platform_url)) == sorted(
            const.STUDENT_TEAMS
        )

    def test_run_twice(self, platform_url):
        """It should be fine to create teams twice."""
        funcs.run_repobee(f"teams create --base-url {platform_url}")
        funcs.run_repobee(f"teams create --base-url {platform_url}")
        assert sorted(funcs.get_student_teams(platform_url)) == sorted(
            const.STUDENT_TEAMS
        )
