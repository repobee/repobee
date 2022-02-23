"""Plugin that enables an extended, YAML-based syntax for the students file.

.. warning::

    This plugin is in early development, and may change without notice. The
    plan is to integrate this functionality directly into RepoBee once we're
    satisfied with how it works.

The point of this plugin is to allow one to specify student teams with more
granularity. In particular, it allows one to specify names independently of
the members of each team. For example, to have a team ``some-team`` with
members alice and eve and another team ``other-team`` with sole member bob,
the following file would do the trick:

.. code-block:: yml
    :caption: students.yml

    some-team:
        members: [alice, bob]
    other-team:
        members: [eve]

Then provide it as the ``--students-file`` with this plugin active, and all
is well!
"""


import sys
import pathlib

from typing import Iterable

import yamliny
import repobee_plug as plug


_MEMBERS_KEY = "members"


@plug.repobee_hook
def parse_students_file(
    students_file: pathlib.Path,
) -> Iterable[plug.StudentTeam]:
    return [
        _to_student_team(name=name, data=data)
        for name, data in _parse_yamliny(students_file).items()
    ]


def _parse_yamliny(students_file: pathlib.Path) -> dict:
    try:
        return yamliny.loads(
            students_file.read_text(encoding=sys.getdefaultencoding())
        )
    except yamliny.YamlinyError as exc:
        raise plug.PlugError(f"Parse error '{students_file}': {exc}") from exc


def _to_student_team(name: str, data: dict) -> plug.StudentTeam:
    if _MEMBERS_KEY not in data:
        raise plug.PlugError(f"Missing members mapping for '{name}'")
    return plug.StudentTeam(name=name, members=data[_MEMBERS_KEY])
