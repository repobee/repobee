"""Plugin functionality for creating extensions to the RepoBee CLI."""
import abc
import collections
import itertools
from typing import List, Tuple, Optional, Set, Mapping, Iterable

from repobee_plug import _containers

__all__ = [
    "Option",
    "Positional",
    "MutuallyExclusiveGroup",
    "Command",
    "CommandExtension",
    "Action",
    "Category",
    "CoreCommand",
    "CommandSettings",
]

from repobee_plug._containers import ImmutableMixin

Option = collections.namedtuple(
    "Option",
    [
        "short_name",
        "long_name",
        "configurable",
        "help",
        "converter",
        "required",
        "default",
        "argparse_kwargs",
    ],
)
Option.__new__.__defaults__ = (None,) * len(Option._fields)

Positional = collections.namedtuple(
    "Positional", ["help", "converter", "argparse_kwargs"]
)
Positional.__new__.__defaults__ = (None,) * len(Positional._fields)


class CommandSettings(_containers.ImmutableMixin):
    """Settings for a :py:class:`Command`, that can be provided in the
    ``__settings__`` attribute.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug

        class Ext(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.CommandSettings(
                action_name="hello",
                category=plug.cli.CoreCommand.config,
            )

            def command_callback(self, args, api):
                print("Hello, world!")

    This can then be called with:

    .. code-block:: bash

        $ repobee -p ext.py config hello
        Hello, world!
    """

    def __init__(
        self,
        action_name: Optional[str] = None,
        category: Optional["CoreCommand"] = None,
        help: str = "",
        description: str = "",
        requires_api: bool = False,
        base_parsers: Optional[List[_containers.BaseParser]] = None,
        config_section_name: Optional[str] = None,
    ):
        """
        Args:
            action_name: The name of the action that the command will be
                available under.
        """
        object.__setattr__(self, "action_name", action_name)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "help", help)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "requires_api", requires_api)
        object.__setattr__(self, "base_parsers", base_parsers)
        object.__setattr__(self, "config_section_name", config_section_name)


class CommandExtensionSettings(_containers.ImmutableMixin):
    """Settings for a :py:class:`CommandExtension`."""

    actions: List["Action"]
    config_section_name: Optional[str]

    def __init__(
        self,
        actions: List["Action"],
        config_section_name: Optional[str] = None,
    ):
        if not actions:
            raise ValueError(
                f"argument 'actions' must be a non-empty list: {actions}"
            )
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "config_section_name", config_section_name)


class MutuallyExclusiveGroup(_containers.ImmutableMixin):
    """A group of mutually exclusive CLI options.

    Attributes:
        ALLOWED_TYPES: The types that are allowed to be passed in the
            constructor kwargs.
        options: The options that have been stored in this group.
        required: Whether or not this mutex group is required.
    """

    ALLOWED_TYPES = (Option,)
    options: List[Tuple[str, Option]]
    required: bool

    def __init__(self, *, __required__: bool = False, **kwargs):
        """
        Args:
            __required__: Whether or not this mutex group is required.
            kwargs: Keyword arguments on the form ``name=plug.cli.Option()``.
        """

        def _check_type(key, value):
            if not isinstance(value, self.ALLOWED_TYPES):
                raise TypeError(
                    f"{value.__class__.__name__} "
                    f"not allowed in mutex group: {key}={value}"
                )
            return True

        options = [
            (key, value)
            for key, value in kwargs.items()
            if _check_type(key, value)
        ]

        object.__setattr__(self, "options", options)
        object.__setattr__(self, "required", __required__)


class CommandExtension:
    """Mixin class for use with the Plugin class. Marks the extending class as
    a command extension, that adds options to an existing command.
    """


class Command:
    """Mixin class for use with the Plugin class. Explicitly marks a class as
    an extension command.

    An extension command must have an callback defined in the class on the
    following form:

    .. code-block:: python

        def command_callback(
            self, args: argparse.Namespace, api: plug.API
        ) -> Optional[plug.Result]:
            pass

    Note that the type hints are not required, so the callback can be defined
    like this instead:

    .. code-block:: python

        def command_callback(self, args, api):
            pass

    Declaring static members of type :py:class:`Option` will add command line
    options to the command, and these are then parsed and passed to the
    callback in the ``args`` object.

    Example usage:

    .. code-block:: python
        :caption: command.py

        import repobee_plug as plug

        class Greeting(plug.Plugin, plug.cli.Command):

            name = plug.cli.Option(
                short_name="-n", help="your name", required=True
            )
            age = plug.cli.Option(
                converter=int, help="your age", default=30
            )

            def command_callback(self, args, api):
                print(f"Hello, my name is {args.name} and I am {args.age}")

    Note that the file is called ``command.py``. We can run this command with
    RepoBee like so:

    .. code-block:: bash

        $ repobee -p command.py greeting -n Alice
        Hello, my name is Alice and I am 30
    """


class Category(ImmutableMixin, abc.ABC):
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

    def get(self, key: str) -> "Action":
        return self._action_table.get(key)

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


class Action(ImmutableMixin):
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

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.name == other.name
            and self.category == other.category
        )

    def __hash__(self):
        return hash(str(self))

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


class _CoreCommand(ImmutableMixin):
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
