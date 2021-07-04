"""Utility functions for dealing with files and directories.

.. module:: fileutil
    :synopsis: Utility functions for dealing with files and directories.
"""
import enum
import pathlib

import repobee_plug as plug

__all__ = ["DirectoryLayout"]


def _flat_repo_path(
    base: pathlib.Path, repo: plug.StudentRepo
) -> pathlib.Path:
    return base / repo.name


def _by_team_repo_path(
    base: pathlib.Path, repo: plug.StudentRepo
) -> pathlib.Path:
    return base / repo.team.name / repo.name


class DirectoryLayout(enum.Enum):
    """Layouts for arranging repositories on disk."""

    FLAT = "flat"
    BY_TEAM = "by-team"

    def __init__(self, label: str):
        self.label = label
        self.get_repo_path = {
            "flat": _flat_repo_path,
            "by-team": _by_team_repo_path,
        }[label]

    def __str__(self):
        return str(self.label)
