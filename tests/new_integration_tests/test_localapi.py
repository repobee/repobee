"""Targeted tests for the LocalAPI implementation."""
import pytest

import repobee_plug as plug
from repobee_testhelpers import const
from repobee_testhelpers import localapi


@pytest.fixture
def api(platform_url):
    return localapi.LocalAPI(
        platform_url, const.TARGET_ORG_NAME, const.TEACHER, const.TOKEN
    )


class TestDeleteRepo:
    def test_delete_existing_repo(self, api):
        # arrange
        repo = api.create_repo("some-repo", "Some description", True)
        assert api.get_repo(repo.name, None)

        # act
        api.delete_repo(repo)

        # assert
        with pytest.raises(plug.NotFoundError):
            api.get_repo(repo.name, None)

    def test_delete_repo_assigned_to_team(self, api):
        # arrange
        api.create_team("smoke-and-mirrors-team")
        team = api.create_team("some-team")
        repo = api.create_repo("some-repo", "Some description", True, team)
        assert next(api.get_team_repos(team)) == repo

        # act
        api.delete_repo(repo)

        # assert
        assert not list(api.get_team_repos(team))

    def test_delete_non_existing_repo(self, api):
        # arrange
        repo = api.create_repo("some-repo", "Some description", True)
        api.delete_repo(repo)

        # act/assert
        with pytest.raises(plug.NotFoundError):
            api.delete_repo(repo)
