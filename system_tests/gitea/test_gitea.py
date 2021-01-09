import pytest

import repobee_plug as plug
from repobee_testhelpers._internal import templates
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


class TestDeleteTeam:
    """Tests for the delete_team function."""

    def test_delete_existing_team(self, target_api):
        team = target_api.create_team("the-team")

        target_api.delete_team(team)

        assert not list(target_api.get_teams([team.name]))


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


class TestGetRepos:
    """Tests for the get_repos function."""

    def test_get_all_repos_from_template_org(self, template_api):
        repos = template_api.get_repos()
        assert sorted(repo.name for repo in repos) == sorted(
            templates.TEMPLATE_REPO_NAMES
        )

    def test_get_template_repos_by_urls(self, template_api):
        # arrange
        expected_repo_names = [
            name for name in templates.TEMPLATE_REPO_NAMES[:-1]
        ]
        repo_urls = template_api.get_repo_urls(list(expected_repo_names))

        # act
        repos = template_api.get_repos(repo_urls)

        # assert
        assert sorted(repo.name for repo in repos) == sorted(
            expected_repo_names
        )


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


class TestCreateIssue:
    """Tests for the create_issue function."""

    def test_create_issue_without_asignees(self, target_api):
        # arrange
        repo = target_api.create_repo("some-repo", "some description", True)
        title = "This is the issue title"
        body = "This is the issue body\nAnd it's the best!"

        # act
        created_issue = target_api.create_issue(
            title=title, body=body, repo=repo
        )

        # assert
        fetched_issue = next(target_api.get_repo_issues(repo))

        assert created_issue.title == title
        assert created_issue.body == body
        assert created_issue.number == 1
        assert created_issue.state == plug.IssueState.OPEN
        assert created_issue.implementation is not None
        assert created_issue == fetched_issue


class TestCloseIssue:
    """tests for the close_issue function."""

    def test_close_open_issue(self, target_api):
        # arrange
        repo = target_api.create_repo("some-repo", "some description", True)
        issue = target_api.create_issue(
            title="issue title", body="issue body", repo=repo
        )

        # act
        target_api.close_issue(issue)

        # assert
        assert (
            next(target_api.get_repo_issues(repo)).state
            == plug.IssueState.CLOSED
        )


class TestGetRepoIssues:
    """Tests for the get_repo_issues function."""

    def test_get_issues_from_repo_without_issues(self, target_api):
        repo = target_api.create_repo("some-repo", "some description", True)

        assert not list(target_api.get_repo_issues(repo))

    def test_get_issues_from_repo_with_multiple_issues(self, target_api):
        # arrange
        repo = target_api.create_repo("some-repo", "some description", True)
        issues = [
            target_api.create_issue(
                title=f"{phrase} issue",
                body=f"body of {phrase} issue",
                repo=repo,
            )
            for phrase in "first second third fourth".split()
        ]
        assert len(issues) == 4, "expected 4 issues before test"

        # act
        fetched_issues = list(target_api.get_repo_issues(repo))

        # assert
        key = lambda issue: issue.number  # noqa
        assert sorted(fetched_issues, key=key) == sorted(issues, key=key)


class TestVerifySettings:
    """Tests for the verify_settings function."""

    def test_prints_great_success_when_all_settings_good(self, capsys):
        gitea.GiteaAPI.verify_settings(
            user=giteamanager.TEACHER_USER,
            org_name=giteamanager.TARGET_ORG_NAME,
            base_url=giteamanager.API_URL,
            token=giteamanager.TEACHER_TOKEN,
            template_org_name=giteamanager.TEMPLATE_ORG_NAME,
        )

        last_line = capsys.readouterr().out.strip().split("\n")[-1]
        assert "GREAT SUCCESS" in last_line

    def test_prints_great_success_when_all_settings_good_without_template_org(
        self, capsys
    ):
        gitea.GiteaAPI.verify_settings(
            user=giteamanager.TEACHER_USER,
            org_name=giteamanager.TARGET_ORG_NAME,
            base_url=giteamanager.API_URL,
            token=giteamanager.TEACHER_TOKEN,
        )

        last_line = capsys.readouterr().out.strip().split("\n")[-1]
        assert "GREAT SUCCESS" in last_line

    def test_raises_on_bad_url(self):
        with pytest.raises(plug.ServiceNotFoundError) as exc_info:
            gitea.GiteaAPI.verify_settings(
                user=giteamanager.TEACHER_USER,
                org_name=giteamanager.TARGET_ORG_NAME,
                base_url=giteamanager.BASE_URL,  # this url is missing /api/v1
                token=giteamanager.TEACHER_TOKEN,
                template_org_name=giteamanager.TEMPLATE_ORG_NAME,
            )

        assert "bad base url" in str(exc_info.value)

    def test_raises_on_bad_token(self):
        with pytest.raises(plug.BadCredentials) as exc_info:
            gitea.GiteaAPI.verify_settings(
                user=giteamanager.TEACHER_USER,
                org_name=giteamanager.TARGET_ORG_NAME,
                base_url=giteamanager.API_URL,
                token="nopetoken",
                template_org_name=giteamanager.TEMPLATE_ORG_NAME,
            )

        assert "bad token" in str(exc_info.value)

    def test_raises_on_token_user_mismatch(self):
        with pytest.raises(plug.BadCredentials) as exc_info:
            gitea.GiteaAPI.verify_settings(
                user=giteamanager.ADMIN_USER,
                token=giteamanager.TEACHER_TOKEN,
                org_name=giteamanager.TARGET_ORG_NAME,
                base_url=giteamanager.API_URL,
                template_org_name=giteamanager.TEMPLATE_ORG_NAME,
            )

        assert (
            f"token does not belong to user '{giteamanager.ADMIN_USER}'"
            in str(exc_info.value)
        )

    def test_raises_on_missing_target_org(self):
        non_existant_org = "nopeorg"
        with pytest.raises(plug.NotFoundError) as exc_info:
            gitea.GiteaAPI.verify_settings(
                user=giteamanager.TEACHER_USER,
                org_name=non_existant_org,
                base_url=giteamanager.API_URL,
                token=giteamanager.TEACHER_TOKEN,
                template_org_name=giteamanager.TEMPLATE_ORG_NAME,
            )

        assert f"could not find organization '{non_existant_org}'" in str(
            exc_info.value
        )
