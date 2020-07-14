"""Container classes and enums.

.. module:: containers
    :synopsis: Container classes and enums.

.. moduleauthor:: Simon Larsén
"""
import collections
import enum
import argparse
import pluggy

from typing import Mapping, Any, Optional, Callable, Iterable, List

import daiquiri

from repobee_plug import _exceptions
from repobee_plug import _apimeta

LOGGER = daiquiri.getLogger(__file__)

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
        LOGGER.warning(
            "the Result.hook attribute is deprecated, use Result.name instead"
        )
        return self.name


def HookResult(hook, status, msg, data=None) -> Result:
    """Backwards compat function.

    .. deprecated:: 0.12.0

        Replaced by :py:class:`Result`.
    """
    LOGGER.warning("HookResult is deprecated and has been replaced by Result")
    return Result(name=hook, status=status, msg=msg, data=data)


class ExtensionParser(argparse.ArgumentParser):
    """An ArgumentParser specialized for RepoBee extension commands."""

    def __init__(self):
        super().__init__(add_help=False)


class BaseParser(enum.Enum):
    """Enumeration of base parsers that an extension command can request to
    have added to it.

    Attributes:
        BASE: Represents the base parser, which includes the ``--user``,
            ``--org-name``, ``--base-url`` and ``--token`` arguments.
        STUDENTS: Represents the students parser, which includes the
            ``--students`` and `--students-file`` arguments.
        REPO_NAMES: Represents the repo names parser, which includes the
            ``--master-repo-names`` argument.
        REPO_DISCOVERY: Represents the repo discovery parser, which adds
            both the ``--master-repo-names`` and the ``--discover-repos``
            arguments.
        MASTER_ORG: Represents the master organization parser, which includes
            the ``--master-org`` argument.
    """

    BASE = "base"
    STUDENTS = "students"
    REPO_NAMES = "repo-names"
    REPO_DISCOVERY = "repo-discovery"
    MASTER_ORG = "master-org"


class ExtensionCommand(
    collections.namedtuple(
        "ExtensionCommand",
        (
            "parser",
            "name",
            "help",
            "description",
            "callback",
            "requires_api",
            "requires_base_parsers",
        ),
    )
):
    """Class defining an extension command for the RepoBee CLI."""

    def __new__(
        cls,
        parser: ExtensionParser,
        name: str,
        help: str,
        description: str,
        callback: Callable[
            [argparse.Namespace, Optional[_apimeta.API]],
            Optional[Mapping[str, Result]],
        ],
        requires_api: bool = False,
        requires_base_parsers: Optional[List[BaseParser]] = None,
    ):
        if not isinstance(parser, ExtensionParser):
            raise _exceptions.ExtensionCommandError(
                "parser must be a {.__name__}".format(ExtensionParser)
            )
        if not callable(callback):
            raise _exceptions.ExtensionCommandError(
                "callback must be a callable"
            )
        if (
            BaseParser.REPO_DISCOVERY in (requires_base_parsers or [])
            and not requires_api
        ):
            raise _exceptions.ExtensionCommandError(
                "must set requires_api=True to use REPO_DISCOVERY base parser"
            )
        return super().__new__(
            cls,
            parser,
            name,
            help,
            description,
            callback,
            requires_api,
            requires_base_parsers,
        )

    # the init method is just for documentation purposes
    def __init__(
        self,
        parser: ExtensionParser,
        name: str,
        help: str,
        description: str,
        callback: Callable[
            [argparse.Namespace, Optional[_apimeta.API]],
            Optional[Mapping[str, Result]],
        ],
        requires_api: bool = False,
        requires_base_parsers: Optional[Iterable[BaseParser]] = None,
    ):
        """
        Args:
            parser: The parser to use for the CLI.
            name: Name of the command.
            help: Text that will be displayed when running ``repobee -h``
            description: Text that will be displayed when calling the ``-h``
                option for this specific command. Should be elaborate in
                describing the usage of the command.
            callback: A callback function that is called if this command is
                used on the CLI. It is passed the parsed namespace and the
                platform API. It may optionally return a result mapping on
                the form (name: str -> List[Result]) that's reported by
                RepoBee.
            requires_api: If True, the base arguments required for the platform
                API are added as options to the extension command, and the
                platform API is then passed to the callback function. It is
                then important not to have clashing option names. If False, the
                base arguments are not added to the CLI, and None is passed in
                place of the API. If you include ``REPO_DISCOVERY`` in
                ``requires_base_parsers``, then you *must* set this to True.
            requires_base_parsers: A list of
                :py:class:`repobee_plug.BaseParser` that decide which base
                parsers are added to this command. For example, setting
                ``requires_base_parsers = [BaseParser.STUDENTS]`` adds the
                ``--students`` and ``--students-file`` options to this
                extension command's parser.
        """
        super().__init__()

    def __eq__(self, other):
        """Two ExtensionCommands are equal if they compare equal in all
        respects except for the parser, as argpars.ArgumentParser instances do
        not implement __eq__.
        """
        _, *rest = self
        _, *other_rest = other
        return rest == other_rest


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
