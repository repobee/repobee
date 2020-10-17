"""Interoperability plugin for using RepoBee with repositories created with
GitHub Classroom.

RepoBee's default naming scheme is ``<team_name>-<assignment_name>``, whereas
GitHub Classroom's naming scheme is ``<assignment_name>-<team_name>``. This
plugin changes RepoBee's naming scheme to conform to the latter, which allows
RepoBee to be used with repositories created by GitHub Classroom.

.. important::

    Some of RepoBee's commands (e.g. the peer review commands) depend on the
    student repositories being added to the corresponding student team. This is
    not something that GitHub Classroom typically does. In order for all of
    RepoBee's commands to work as expected, you must execute the ``repos
    setup`` command for all assignments that you want to work with.

.. important::

    You should not use this plugin to create repositories, and expect GitHub
    Classroom to recognize them as student repositories. To be very clear,
    Classroom *does not* recognize repositories created by RepoBee as student
    repositories.
"""
from typing import Union

import repobee_plug as plug


PLUGIN_DESCRIPTION = """Allows interoperability with repositories created
by GitHub Classroom by changing RepoBee's naming scheme to conform to that
of Classroom. For each assignment you want to work with, you should run `repos
setup` to add the student repositories to the corresponding student teams, as
GitHub Classroom does not do this.""".replace(
    "\n", " "
)


@plug.repobee_hook
def generate_repo_name(
    team_name: Union[str, plug.StudentTeam, plug.Team], assignment_name: str
) -> str:
    return f"{assignment_name}-{team_name}"
