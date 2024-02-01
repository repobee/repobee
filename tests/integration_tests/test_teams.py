"""Tests for the teams category of commands."""

import sys

import repobee_plug as plug

from repobee_testhelpers import funcs
from repobee_testhelpers import const

import _repobee.ext.studentsyml


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

    def test_run_with_extended_students_syntax(self, platform_url, tmp_path):
        students_file = tmp_path / "students.yml"
        students_file.write_text(
            """
some-team:
    members: [simon]
other-team:
    members: [eve, alice]
        """.strip(),
            encoding=sys.getdefaultencoding(),
        )
        expected_teams = [
            plug.StudentTeam(name="some-team", members=["simon"]),
            plug.StudentTeam(name="other-team", members=["eve", "alice"]),
        ]

        funcs.run_repobee(
            f"{plug.cli.CoreCommand.teams.create} --base-url {platform_url} "
            f"--students-file {students_file}",
            plugins=[_repobee.ext.studentsyml],
        )

        assert sorted(funcs.get_student_teams(platform_url)) == sorted(
            expected_teams
        )
