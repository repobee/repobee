"""Plugin that provides the default students file parsing for RepoBee.

.. module:: students_file_parser
    :synopsis: Default students file parsing for RepoBee.
"""

import os
import pathlib
import sys

from typing import Iterable

import repobee_plug as plug


@plug.repobee_hook
def parse_students_file(
    students_file: pathlib.Path,
) -> Iterable[plug.StudentTeam]:
    return [
        plug.StudentTeam(members=group.strip().split())
        for group in students_file.read_text(
            encoding=sys.getdefaultencoding()
        ).split(os.linesep)
        if group  # skip blank lines
    ]
