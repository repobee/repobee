"""Hook specifications and containers."""
import collections
import enum

from typing import Optional, Mapping, Any

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
