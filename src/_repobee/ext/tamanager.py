"""Plugin for managing teaching assistants' access to student repos.

.. note::

    We recommend to activate this plugin persistently. See
    :ref:`activate_plugins` for how to do that.

.. warning::

    This plugin is currently experimental, and may change in coming releases.
    We encourage you to use it, but be prepared that even a minor version
    update of RepoBee may come with breaking changes to the interface of this
    plugin.

Originally, RepoBee was designed such that all teachers and teaching assistants
using it were supposed to be owners of the target organization. This has proven
inconvenient at times, as the course responsible may not be comfortable giving
admin powers to each and every teacher/TA. The purpose of this plugin is to
allow teaching assistants and teachers (we will say just *teachers* from this
point on) to be given read-access to the student repositories of a target
organization, without any further privileges.

There are two primary pieces of functionality. First, the ``add-teachers``
action is added to the ``teams`` category (i.e. the command ``teams
add-teachers`` now exists). This command must be executed at least once,
and provides read-access for the specified teachers. It does so by adding
specified TAs to a team called *repobee-teachers*, and then adding **all**
repositories in the target organization to said team. See ``repobee teams
add-teachers --help`` for specifics on usage.

The second piece of functionality is a hook that runs each time the ``repos
setup`` command is executed. It adds any newly created student repos to the
*repobee-teachers* team. For this to work, the plugin *must be activated
persistently*. See :ref:`activate_plugins` for details on activating plugins.

To summarize usage, you should use this plugin like so.

1. Activate the plugin persistently.
2. Run the ``teams add-teachers`` command to set everything up.

.. important::

    If you use RepoBee in discovery mode, i.e. students create their own repos
    and add them to their teams, then you must re-execute ``teams
    add-teachers`` periodically to give teachers access to the newly created
    repos. It's only when dictate mode is used, i.e. you setup repos with
    ``repos setup``, that the new repos are automatically added to the
    *repobee-teachers* team.
"""
from typing import Optional

import repobee_plug as plug


TEACHERS_TEAM_NAME = "repobee-teachers"

PLUGIN_DESCRIPTION = """Manager plugin for adding and removing
teachers/teaching assistants from the taget organization. Teachers are granted
read access to all repositories in the organization. This plugin should not be
used with GitLab due to performance issues. (NOTE: This plugin is not stable
yet and may change without notice)""".replace(
    "\n", " "
)

_ADD_TEACHERS_DESCRIPTION = f"""
Add teachers/teaching assistants to the `{TEACHERS_TEAM_NAME}` team. This team
is in turn granted read access to all repositories in the organization. The
point of this is to allow a course responsible to allow teaching assistants to
access student repositories without being able to manipulate them. To revoke
read access, simply manually remove users from `{TEACHERS_TEAM_NAME}`.
""".replace(
    "\n", " "
)


class AddTeachers(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        category=plug.cli.CoreCommand.teams,
        action="add-teachers",
        help="add teachers/teaching assistants to the organization, with read "
        "access to all repositories",
        description=_ADD_TEACHERS_DESCRIPTION,
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
