import pytest

from _repobee.ext import gitea

import giteamanager


@pytest.fixture
def gitea_api():
    return gitea.GiteaAPI(
        giteamanager.API_URL,
        giteamanager.TEACHER_USER,
        giteamanager.TEACHER_TOKEN,
        giteamanager.TARGET_ORG_NAME,
    )


class TestCreateTeam:
    """Tests for the create_team function."""

    def test_create_non_existing_team(self, gitea_api):
        team_name = "best-team"

        gitea_api.create_team(team_name)

        assert (
            next(gitea_api.get_teams(team_names=[team_name])).name == team_name
        )

    def test_create_team_with_members(self, gitea_api):
        # arrange
        members = "mema memb memc memd".split()
        for member in members:
            giteamanager.create_user(member)

        team_name = "best-team"

        # act
        gitea_api.create_team(team_name, members=members)

        # assert
        fetched_team = next(gitea_api.get_teams([team_name]))
        assert sorted(fetched_team.members) == sorted(members)


class TestGetTeams:
    """Tests for the get_teams function."""

    def test_get_owners_team(self, gitea_api):
        owners_team_name = "Owners"
        matches = list(gitea_api.get_teams(team_names=[owners_team_name]))

        assert len(matches) == 1
        assert matches[0].name == owners_team_name
        assert matches[0].members == [giteamanager.TEACHER_USER]

    def test_get_all_default_teams(self, gitea_api):
        """Test getting the default teams of an organization (which
        is only the owners team), without specifying any team
        names.
        """
        all_teams = list(gitea_api.get_teams())

        assert len(all_teams) == 1
        assert all_teams[0].name == "Owners"

    def test_get_100_teams(self, gitea_api):
        # arrange
        team_names = list(map(str, range(100)))
        for team_name in team_names:
            gitea_api.create_team(team_name)

        # act
        fetched_team_names = [team.name for team in gitea_api.get_teams()]

        # assert
        assert sorted(fetched_team_names) == sorted(team_names + ["Owners"])
