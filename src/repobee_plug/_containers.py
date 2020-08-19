"""Container classes and enums.

.. module:: containers
    :synopsis: Container classes and enums.
"""
import collections
import dataclasses
import enum

from typing import Mapping, Any, Optional, List

import pluggy  # type: ignore

from repobee_plug import log

hookspec = pluggy.HookspecMarker(__package__)
hookimpl = pluggy.HookimplMarker(__package__)


class Status(enum.Enum):
    """Status codes enums for Results.

    Attributes:
        SUCCESS: Signifies a plugin execution without any complications.
        WARNING: Signifies a plugin execution with non-critical failures.
        ERROR: Signifies a critical error during execution.
    """

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Result(
    collections.namedtuple("Result", ("name", "status", "msg", "data"))
):
    """Container for storing results from hooks."""

    def __new__(
        cls,
        name: str,
        status: Status,
        msg: str,
        data: Optional[Mapping[Any, Any]] = None,
    ):
        return super().__new__(cls, name, status, msg, data)

    def __init__(
        self,
        name: str,
        status: Status,
        msg: str,
        data: Optional[Mapping[Any, Any]] = None,
    ):
        """
        Args:
            name: Name to associate with this result. This is typically the
                name of the plugin that returns this result.
            status: Status of the plugin execution.
            msg: A free-form result message.
            data: Semi-structured data in the form of a dictionary. All of the
                contents of the dictionary should be serializable as this is
                primarily used for JSON storage.
        """
        super().__init__()

    @property
    def hook(self) -> str:
        log.warning(
            "the Result.hook attribute is deprecated, use Result.name instead"
        )
        return self.name


def HookResult(hook, status, msg, data=None) -> Result:
    """Backwards compat function.

    .. deprecated:: 0.12.0

        Replaced by :py:class:`Result`.
    """
    log.warning("HookResult is deprecated and has been replaced by Result")
    return Result(name=hook, status=status, msg=msg, data=data)


class BaseParser(enum.Enum):
    """Enumeration of base parsers that an extension command can request to
    have added to it.

    Attributes:
        BASE: Represents the base parser, which includes the ``--user``,
            ``--org-name``, ``--base-url`` and ``--token`` arguments.
        STUDENTS: Represents the students parser, which includes the
            ``--students`` and `--students-file`` arguments.
        ASSIGNMENTS: Represents the assignments parser, which includes the
            ``--assignments`` argument.
        REPO_DISCOVERY: Represents the repo discovery parser, which adds
            both the ``--assignments`` and the ``--discover-repos``
            arguments.
        TEMPLATE_ORG: Represents the master organization parser, which includes
            the ``--master-org`` argument.
    """

    BASE = "base"
    STUDENTS = "students"
    ASSIGNMENTS = "assignments"
    REPO_DISCOVERY = "repo-discovery"
    TEMPLATE_ORG = "template-org"


class ImmutableMixin:
    """Make a class (more or less) immutable."""

    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__class__} is immutable")

    def __setattribute__(self, name, value):
        self.__setattr__(name, value)


ReviewAllocation = collections.namedtuple(
    "ReviewAllocation", "review_team reviewed_team"
)
ReviewAllocation.__doc__ = """
Args:
    review_team (Team): The team of reviewers.
    reviewed_team (Team): The team that is to be reviewed.
"""

Review = collections.namedtuple("Review", ["repo", "done"])
Review.__doc__ = """
Args:
    repo (Repo): The reviewed repository.
    done (bool): Whether or not the review is done.
"""

Deprecation = collections.namedtuple(
    "Deprecation", ["replacement", "remove_by_version"]
)
Deprecation.__doc__ = """
Args:
    replacement (str): The functionality that replaces the deprecated
        functionality.
    remove_by_version (str): A version number on the form
        ``MAJOR.MINOR.PATCH`` by which the deprecated functionality will be
        removed.
"""


@dataclasses.dataclass(frozen=True)
class ConfigurableArguments:
    """A container for holding a plugin's configurable arguments."""

    config_section_name: str
    argnames: List[str]
