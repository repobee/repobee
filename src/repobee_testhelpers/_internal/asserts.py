"""Reusable asserts for system tests."""
import itertools
import pathlib

from typing import List

import repobee_plug as plug

from repobee_testhelpers.funcs import hash_directory
from repobee_testhelpers._internal import templates


def assert_cloned_repos(
    student_teams: List[plug.StudentTeam],
    template_repo_names: List[str],
    tmpdir: pathlib.Path,
) -> None:
    """Check that the cloned repos have the expected contents.

    NOTE: Only checks the contents of the root of the project.
    """
    # group by master repo name, all of which have the same length
    root = pathlib.Path(tmpdir).resolve()
    for student_team, template_repo_name in itertools.product(
        student_teams, template_repo_names
    ):
        path = plug.fileutils.generate_repo_path(
            root, student_team.name, template_repo_name
        )
        expected_sha = templates.TASK_CONTENTS_SHAS[template_repo_name]
        sha = hash_directory(path)
        assert sha == expected_sha
        assert (path / ".git").is_dir()
