"""Local representations of API objects."""
import dataclasses
import pathlib

from typing import Optional, List

from repobee_plug import exceptions

MAX_NAME_LENGTH = 100

__all__ = ["StudentTeam", "StudentRepo", "TemplateRepo"]


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


class _RepoPathMixin:
    """Mixin class for local repo representations that provides a path
    attribute, which may not be set.
    """

    _path: Optional[pathlib.Path]

    def __init__(self, *ars, **kwargs):
        pass

    def with_path(self, path: pathlib.Path) -> "_RepoPathMixin":
        """Return a copy of this repo, with a different path.

        Args:
            path: Path to the local copy of this repo.
        Returns:
            A copy of this repo representation, with the specified path.
        """
        # must not use dataclasses.asdict, as it recursively operates on
        # dataclass members
        data_dict = {
            field.name: getattr(self, field.name)
            for field in dataclasses.fields(self)
        }
        data_dict["_path"] = path
        return self.__class__(**data_dict)

    @property
    def path(self) -> pathlib.Path:
        if not self._path:
            raise exceptions.PlugError("path not set")
        return self._path


@dataclasses.dataclass(frozen=True)
class StudentRepo(_RepoPathMixin):
    """Local representation of a student repo.

    Attributes:
        name: Name of this repository.
        team: The team this repository belongs to.
        url: URL to the platform repository.
        path: Path to the local copy of this repository.
    """

    name: str
    team: StudentTeam
    url: str
    _path: Optional[pathlib.Path] = None

    def __post_init__(self):
        _check_name_length(self.name)


@dataclasses.dataclass(frozen=True)
class TemplateRepo(_RepoPathMixin):
    """Local representation of a template repo.

    Attributes:
        name: Name of this repository.
        url: URL to the platform repository.
        path: Path to the local copy of this repository.
        file_uri: File URI to the local copy of this repository.
    """

    name: str
    url: str
    _path: Optional[pathlib.Path] = None

    @property
    def file_uri(self):
        p = f"file://{self.path}"
        print(p)
        return f"file://{self.path}"
