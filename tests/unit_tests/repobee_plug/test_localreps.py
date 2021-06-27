"""Tests of the localreps classes and functions."""

import repobee_plug as plug


class TestStudentTeam:
    """Tests for the StudentTeam class."""

    def test_constructor_lowercases_member_names(self):
        members = ["siMON", "alIce", "EVE"]
        members_lowercase = ["simon", "alice", "eve"]
        team = plug.StudentTeam(members=members)
        assert team.members == members_lowercase


class TestStudentRepo:
    """Tests for the StudentRepo class"""

    def test_constructor_lowercases_name(self):
        name = "TeStREpo"
        name_lowercase = "testrepo"

        members = ["simon", "alice", "eve"]
        team = plug.StudentTeam(members=members)
        url = "https://github.com/SpoonLabs/diffmin"

        student_repo = plug.StudentRepo(name, team, url)
        assert student_repo.name == name_lowercase

    def test_constructor_lowercases_url(self):
        name = "testrepo"
        members = ["simon", "alice", "eve"]
        team = plug.StudentTeam(members=members)

        url = "hTTpS://GitHub.com/spoOnLaBs/DiFfMIN"
        url_lowercase = "https://github.com/spoonlabs/diffmin"

        student_repo = plug.StudentRepo(name, team, url)
        assert student_repo.url == url_lowercase
