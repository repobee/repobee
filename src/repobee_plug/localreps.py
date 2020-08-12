"""Local representations of API objects."""
import dataclasses
import pathlib

from typing import Optional, List

MAX_NAME_LENGTH = 100

__all__ = ["StudentTeam", "StudentRepo"]


def _check_name_length(name):
    """Check that a Team/Repository name does not exceed the maximum GitHub
    allows (100 characters)
    """
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(
            "generated Team/Repository name is too long, was {} chars, "
            "max is {} chars".format(len(name), MAX_NAME_LENGTH)
        )


@dataclasses.dataclass(frozen=True, order=True)
class StudentTeam:
    """Local representation of a student team.

    Attributes:
        members: A list of members of this team.
        name: The name of this team.
    """

    members: List[str] = dataclasses.field(compare=False)
    name: str = dataclasses.field(default="", compare=True)

    def __str__(self):
        return self.name

    def __post_init__(self):
        object.__setattr__(self, "memebers", list(self.members))
        object.__setattr__(
            self, "name", self.name or "-".join(sorted(self.members))
        )
        _check_name_length(self.name)


@dataclasses.dataclass(frozen=True)
class StudentRepo:
    """Local representation of a student repo.

    Attributes:
        name: Name of this repository.
        team: The team this repository belongs to.
        url: URL to the platform repository.
        path: Path to the local repository if it exists on disc.
    """

    name: str
    team: StudentTeam
    url: str
    path: Optional[pathlib.Path] = None

    def __post_init__(self):
        _check_name_length(self.name)
