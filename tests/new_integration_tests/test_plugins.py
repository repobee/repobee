"""Integration tests for plugin functionality."""

import repobee_plug as plug

from repobee_testhelpers import funcs
from repobee_testhelpers import const


def test_create_repo_with_plugin(platform_url):
    team = const.STUDENT_TEAMS[0]
    repo_name = "super-repo"
    description = "This is the description"
    private = True

    class CreateSingle(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            category=plug.cli.CoreCommand.repos, action="create-single"
        )
        team_name = plug.cli.option()
        repo_name = plug.cli.option()

        def command(self, api: plug.PlatformAPI):
            team = api.get_teams(team_names=[self.team_name])
            api.create_repo(
                self.repo_name,
                description=description,
                private=private,
                team=team,
            )

    funcs.run_repobee(
        f"repos create-single --bu {platform_url} "
        f"--team-name {team.name} --repo-name {repo_name}",
        plugins=[CreateSingle],
    )

    existing_repos = funcs.get_repos(platform_url)

    matching_repo = next(
        (repo for repo in existing_repos if repo.name == repo_name), None
    )

    assert matching_repo.name == repo_name
    assert matching_repo.description == description
    assert matching_repo.private == private
