import pytest

from repobee_testhelpers._internal import templates

import repobee_plug as plug

from _repobee.ext import gitea

import giteamanager


@pytest.fixture
def target_api():
    return gitea.GiteaAPI(
        giteamanager.API_URL,
        giteamanager.TEACHER_USER,
        giteamanager.TEACHER_TOKEN,
        giteamanager.TARGET_ORG_NAME,
    )


@pytest.fixture
def template_api():
    return gitea.GiteaAPI(
        giteamanager.API_URL,
        giteamanager.TEACHER_USER,
        giteamanager.TEACHER_TOKEN,
        giteamanager.TEMPLATE_ORG_NAME,
    )


class TestCreateTeam:
    """Tests for the create_team function."""

    def test_create_non_existing_team(self, target_api):
        team_name = "best-team"

        target_api.create_team(team_name)

        assert (
            next(target_api.get_teams(team_names=[team_name])).name
            == team_name
        )

    def test_create_team_with_members(self, target_api):
        # arrange
        members = "mema memb memc memd".split()
        for member in members:
            giteamanager.create_user(member)

        team_name = "best-team"

        # act
        target_api.create_team(team_name, members=members)

        # assert
        fetched_team = next(target_api.get_teams([team_name]))
        assert sorted(fetched_team.members) == sorted(members)


class TestGetTeams:
    """Tests for the get_teams function."""

    def test_get_owners_team(self, target_api):
        owners_team_name = "Owners"
        matches = list(target_api.get_teams(team_names=[owners_team_name]))

        assert len(matches) == 1
        assert matches[0].name == owners_team_name
        assert matches[0].members == [giteamanager.TEACHER_USER]

    def test_get_all_default_teams(self, target_api):
        """Test getting the default teams of an organization (which
        is only the owners team), without specifying any team
        names.
        """
        all_teams = list(target_api.get_teams())

        assert len(all_teams) == 1
        assert all_teams[0].name == "Owners"

    def test_get_100_teams(self, target_api):
        # arrange
        team_names = list(map(str, range(100)))
        for team_name in team_names:
            target_api.create_team(team_name)

        # act
        fetched_team_names = [team.name for team in target_api.get_teams()]

        # assert
        assert sorted(fetched_team_names) == sorted(team_names + ["Owners"])


class TestCreateRepo:
    """Tests for the create_repo function."""

    def test_create_non_existing_public_repo(self, target_api):
        name = "best-repo"
        description = "The best repo ever!"
        private = False

        created_repo = target_api.create_repo(
            name=name, description=description, private=private
        )

        assert created_repo.name == name
        assert created_repo.description == description
        assert created_repo.private == private
        assert target_api.get_repo(name, None) == created_repo

    def test_raises_on_create_existing_repo(self, template_api):
        repo_name = templates.TEMPLATE_REPO_NAMES[0]

        with pytest.raises(plug.PlatformError) as exc_info:
            template_api.create_repo(
                repo_name, description="description", private=True, team=None
            )

        assert exc_info.value.status == 409


class TestGetRepo:
    """Tests for the get_repo function."""

    def test_get_existing_repo(self, template_api):
        repo_name = templates.TEMPLATE_REPO_NAMES[0]

        assert template_api.get_repo(repo_name, None).name == repo_name

    def test_raises_on_get_non_existing_repo(self, target_api):
        with pytest.raises(plug.PlatformError) as exc_info:
            target_api.get_repo("non-existing-repo", None)

        assert exc_info.value.status == 404


class TestAssignRepo:
    """Tests for the assign_repo function."""

    def test_assign_existing_repo_to_existing_team(self, target_api):
        # arrange
        repo = target_api.create_repo(
            "best-repo", description="some description", private=True
        )
        team = target_api.create_team("best-team")

        # act
        target_api.assign_repo(team, repo, permission=plug.TeamPermission.PUSH)

        # assert
        team_repo, *rest = list(target_api.get_team_repos(team))
        assert team_repo == repo
        assert not rest


class TestGetTeamRepos:
    """Tests for the get_team_repos function."""

    def test_get_repos_from_team_without_repos(self, target_api):
        # arrange
        team = target_api.create_team("best-team")

        # act
        team_repos = list(target_api.get_team_repos(team))

        # assert
        assert not team_repos

    def test_get_repos_from_team_with_repos(self, target_api):
        # arrange
        team = target_api.create_team("best-team")
        repos = [
            target_api.create_repo(
                name, description="some description", private=True
            )
            for name in "a b c d".split()
        ]
        for repo in repos:
            target_api.assign_repo(
                team, repo, permission=plug.TeamPermission.PUSH
            )

        # act
        team_repos = target_api.get_team_repos(team)

        # assert
        assert sorted(t.name for t in team_repos) == sorted(
            t.name for t in repos
        )
