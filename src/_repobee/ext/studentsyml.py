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

import yamliny
import repobee_plug as plug

from typing import Iterable


@plug.repobee_hook
def parse_students_file(
    students_file: pathlib.Path,
) -> Iterable[plug.StudentTeam]:
    try:
        students_dict = yamliny.loads(
            students_file.read_text(encoding=sys.getdefaultencoding())
        )
    except yamliny.YamlinyError as exc:
        raise plug.PlugError(f"Parse error '{students_file}': {exc}") from exc
    return [
        plug.StudentTeam(name=name, members=data["members"])
        for name, data in students_dict.items()
    ]
