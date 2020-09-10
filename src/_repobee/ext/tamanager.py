"""Plugin for managing teaching assistants' access to student repos."""
from typing import Optional

import repobee_plug as plug


TEACHERS_TEAM_NAME = "repobee-teachers"

PLUGIN_DESCRIPTION = """Manager plugin for adding and removing
teachers/teaching assistants from the taget organization. Teachers are granted
read access to all repositories in the organization. This plugin only supports
GitHub. (NOTE: This plugin is not stable yet and may
change without notice)""".replace(
    "\n", " "
)


class AddTeachers(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        category=plug.cli.CoreCommand.teams,
        action="add-teachers",
        help="add teachers/teaching assistants to the organization, with read "
        "access to all repositories",
        description="Add teachers/teaching assistants to the "
        "`repobee-teachers` team, which in turn is granted read access to "
        "all repositories in the target organization.",
    )

    teachers = plug.cli.option(
        help="one or more teachers to add", argparse_kwargs=dict(nargs="+")
    )

    def command(self, api: plug.PlatformAPI) -> Optional[plug.Result]:
        teachers_team = _get_or_create_team(TEACHERS_TEAM_NAME, api)
        existing_members = teachers_team.members
        new_members = list(set(self.teachers) - set(existing_members))

        api.assign_members(
            teachers_team, new_members, permission=plug.TeamPermission.PULL
        )

        for repo in plug.cli.io.progress_bar(
            api.get_repos(), desc="Granting read access to repos"
        ):
            api.assign_repo(
                repo=repo,
                team=teachers_team,
                permission=plug.TeamPermission.PULL,
            )

        msg = (
            f"Added {', '.join(new_members)} to the '{TEACHERS_TEAM_NAME}' "
            "team"
        )
        return plug.Result(
            name="add-teachers", status=plug.Status.SUCCESS, msg=msg
        )

    def post_setup(self, repo: plug.StudentRepo, api: plug.PlatformAPI):
        """Add a created student repo to the teachers team."""
        platform_repo = next(iter(api.get_repos([repo.url])))
        teachers_team = _get_or_create_team(TEACHERS_TEAM_NAME, api)

        api.assign_repo(
            team=teachers_team,
            repo=platform_repo,
            permission=plug.TeamPermission.PULL,
        )
        return plug.Result(
            name="tamanager",
            status=plug.Status.SUCCESS,
            msg=f"Added to the {TEACHERS_TEAM_NAME} team",
        )


def _get_or_create_team(team_name: str, api: plug.PlatformAPI) -> plug.Team:
    matches = api.get_teams(team_names=[team_name])

    try:
        return next(iter(matches))
    except StopIteration:
        return api.create_team(
            TEACHERS_TEAM_NAME, permission=plug.TeamPermission.PULL
        )
