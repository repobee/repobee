"""Container classes and enums.

.. module:: containers
    :synopsis: Container classes and enums.

.. moduleauthor:: Simon Larsén
"""
import collections
import enum
import argparse
import pluggy
import itertools
import abc

from typing import Mapping, Any, Optional, Callable, Iterable, List, Tuple, Set

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


class _ImmutableMixin:
    """Make a class (more or less) immutable."""

    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__class__} is immutable")

    def __setattribute__(self, name, value):
        self.__setattr__(name, value)


class Category(_ImmutableMixin, abc.ABC):
    """Class describing a command category for RepoBee's CLI. The purpose of
    this class is to make it easy to programmatically access the different
    commands in RepoBee.

    A full command in RepoBee typically takes the following form:

    .. code-block:: bash

        $ repobee <category> <action> [options ...]

    For example, the command ``repobee issues list`` has category ``issues``
    and action ``list``. Actions are unique only within their category.

    Attributes:
        name: Name of this category.
        actions: A tuple of names of actions applicable to this category.
    """

    name: str
    actions: Tuple["Action"]
    action_names: Set[str]
    _action_table: Mapping[str, "Action"]

    def __init__(self):
        # determine the name of this category based on the runtime type of the
        # inheriting class
        name = self.__class__.__name__.lower().strip("_")
        # determine the action names based on type annotations in the
        # inheriting class
        action_names = {
            name
            for name, tpe in self.__annotations__.items()
            if issubclass(tpe, Action)
        }

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "action_names", set(action_names))
        # This is just to reserve the name 'actions'
        object.__setattr__(self, "actions", None)

        for key in self.__dict__.keys():
            if key in action_names:
                raise ValueError(f"Illegal action name: {key}")

        actions = []
        for action_name in action_names:
            action = Action(action_name.replace("_", "-"), self)
            object.__setattr__(self, action_name, action)
            actions.append(action)

        object.__setattr__(self, "actions", tuple(actions))
        object.__setattr__(self, "_action_table", {a.name: a for a in actions})

    def __getitem__(self, key: str) -> "Action":
        return self._action_table[key]

    def __iter__(self) -> Iterable["Action"]:
        return iter(self.actions)

    def __len__(self):
        return len(self.actions)

    def __repr__(self):
        return f"Category(name={self.name}, actions={self.action_names})"

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(repr(self))


class Action(_ImmutableMixin):
    """Class describing a RepoBee CLI action.

    Attributes:
        name: Name of this action.
        category: The category this action belongs to.
    """

    name: str
    category: Category

    def __init__(self, name: str, category: Category):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)

    def __repr__(self):
        return f"<Action(name={self.name},category={self.category})>"

    def __str__(self):
        return f"{self.category.name} {self.name}"

    def asdict(self) -> Mapping[str, str]:
        """This is a convenience method for testing that returns a dictionary
        on the following form:

        .. code-block:: python

            {"category": self.category.name "action": self.name}

        Returns:
            A dictionary with the name of this action and its category.
        """
        return {"category": self.category.name, "action": self.name}

    def astuple(self) -> Tuple[str, str]:
        """This is a convenience method for testing that returns a tuple
        on the following form:

        .. code-block:: python

            (self.category.name, self.name)

        Returns:
            A dictionary with the name of this action and its category.
        """
        return (self.category.name, self.name)


class _CoreCommand(_ImmutableMixin):
    """Parser category signifying where an extension parser belongs."""

    def iter_actions(self) -> Iterable[Action]:
        """Iterate over all command actions."""
        return iter(self)

    def __call__(self, key):
        category_map = {c.name: c for c in self._categories}
        if key not in category_map:
            raise ValueError(f"No such category: '{key}'")
        return category_map[key]

    def __iter__(self) -> Iterable[Action]:
        return itertools.chain.from_iterable(map(iter, self._categories))

    def __len__(self):
        return sum(map(len, self._categories))

    @property
    def _categories(self):
        return [
            attr
            for attr in self.__class__.__dict__.values()
            if isinstance(attr, Category)
        ]

    class _Repos(Category):
        setup: Action
        update: Action
        clone: Action
        migrate: Action
        create_teams: Action

    class _Issues(Category):
        open: Action
        close: Action
        list: Action

    class _Config(Category):
        show: Action
        verify: Action

    class _Reviews(Category):
        assign: Action
        check: Action
        end: Action

    repos = _Repos()
    issues = _Issues()
    config = _Config()
    reviews = _Reviews()


CoreCommand = _CoreCommand()


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
            "category",
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
        category: Optional[CoreCommand] = None,
    ):
        if not (isinstance(parser, ExtensionParser) or callable(parser)):
            raise _exceptions.ExtensionCommandError(
                "parser must be callable or a {.__name__}".format(
                    ExtensionParser
                )
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
            category,
        )

    # the init method is just for documentation purposes
    def __init__(
        self,
        parser: ExtensionParser,
        name: str,
        help: str,
        description: str,
        callback: Callable[
            [argparse.Namespace, Optional[_apimeta.API]], Optional[Result]
        ],
        requires_api: bool = False,
        requires_base_parsers: Optional[Iterable[BaseParser]] = None,
        category: Optional[CoreCommand] = None,
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
                platform API. It may optionally return a plugin result that's
                reported by RepoBee's CLI.
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
            category: The category to place this parser in. If ``None``, this
                becomes a top-level command.
        """
        super().__init__()

    def __eq__(self, other):
        """Two ExtensionCommands are equal if they compare equal in all
        respects except for the parser, as argpars.ArgumentParser instances do
        not implement __eq__.
        """
        if not isinstance(other, self.__class__):
            return False
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
