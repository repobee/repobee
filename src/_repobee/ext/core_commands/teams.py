"""WIP rewrite of the teams category.

.. module:: teams
    :synopsis: Implementations of the teams category of commands.
"""
import repobee_plug as plug

from _repobee.ext.core_commands import _options
from _repobee import command


class CreateCommand(plug.Plugin, plug.cli.Command):
    _is_core_command = True

    __settings__ = plug.cli.command_settings(
        action=plug.cli.CoreCommand.teams.create,
        help="create student teams without creating repos",
        description=(
            "Only create student teams. This is intended for when you want to "
            "use RepoBee for management, but don't want to dictate the names "
            "of your student's repositories. The `setup` command performs "
            "this step automatically, so there is never a need to run both "
            "this command AND `setup`."
        ),
        config_section_name="repobee",
    )

    students_mutex = _options.students_mutex()

    def command(self, api: plug.PlatformAPI):
        list(
            plug.cli.io.progress_bar(
                command.create_teams(
                    self.args.students, plug.TeamPermission.PUSH, api
                ),
                desc="Creating teams",
                unit="teams",
                total=len(self.args.students),
            )
        )
