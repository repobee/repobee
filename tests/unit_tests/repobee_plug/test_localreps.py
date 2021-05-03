"""Tests of the localreps classes and functions."""

import repobee_plug as plug


class TestStudentTeam:
    """Tests for the StudentTeam class."""

    def test_constructor_lowercases_member_names(self):
        members = ["siMON", "alIce", "EVE"]
        members_lowercase = ["simon", "alice", "eve"]
        team = plug.StudentTeam(members=members)
        assert team.members == members_lowercase
