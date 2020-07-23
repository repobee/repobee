"""Plugin functionality for creating extensions to the RepoBee CLI."""
import abc
import collections
import enum
import itertools
from typing import List, Tuple, Optional, Set, Mapping, Iterable, Any, Callable

from repobee_plug import _containers


__all__ = [
    "option",
    "positional",
    "mutually_exclusive_group",
    "command_settings",
    "command_extension_settings",
    "Command",
    "CommandExtension",
    "Action",
    "Category",
    "CoreCommand",
]

from repobee_plug._containers import ImmutableMixin


class ArgumentType(enum.Enum):
    OPTION = "Option"
    POSITIONAL = "Positional"
    MUTEX_GROUP = "Mutex"


_Option = collections.namedtuple(
    "Option",
    [
        "short_name",
        "long_name",
        "configurable",
        "help",
        "converter",
        "required",
        "default",
        "argument_type",
        "argparse_kwargs",
    ],
)
_Option.__new__.__defaults__ = (None,) * len(_Option._fields)

_CommandSettings = collections.namedtuple(
    "_CommandSettings",
    [
        "action_name",
        "category",
        "help",
        "description",
        "requires_api",
        "base_parsers",
        "config_section_name",
    ],
)


_CommandExtensionSettings = collections.namedtuple(
    "_CommandExtensionSettings", ["actions", "config_section_name"]
)


def command_settings(
    action_name: Optional[str] = None,
    category: Optional["CoreCommand"] = None,
    help: str = "",
    description: str = "",
    requires_api: bool = False,
    base_parsers: Optional[List[_containers.BaseParser]] = None,
    config_section_name: Optional[str] = None,
) -> _CommandSettings:
    """Create a settings object for a :py:class:`Command`.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug

        class Ext(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(
                action_name="hello",
                category=plug.cli.CoreCommand.config,
            )

            def command_callback(self, args, api):
                print("Hello, world!")

    This can then be called with:

    .. code-block:: bash

        $ repobee -p ext.py config hello
        Hello, world!

    Args:
        action_name: The name of the action that the command will be
            available under. Defaults to the name of the plugin class.
        category: The category to place this command in. If not specified,
            then the command will be top-level (i.e. uncategorized).
        help: A help section for the command. This appears when listing the
            help section of the command's category.
        description: A help section for the command. This appears when
            listing the help section for the command itself.
        requires_api: If True, a platform API will be insantiated and
            passed to the command function.
        base_parsers: A list of base parsers to add to the command.
        config_section_name: The name of the configuration section the
            command should look for configurable options in. Defaults
            to the name of the plugin the command is defined in.
    """
    return _CommandSettings(
        action_name=action_name,
        category=category,
        help=help,
        description=description,
        requires_api=requires_api,
        base_parsers=base_parsers,
        config_section_name=config_section_name,
    )


def command_extension_settings(
    actions: List["Action"], config_section_name: Optional[str] = None
) -> _CommandExtensionSettings:
    """Settings for a :py:class:`CommandExtension`.

    Args:
        actions: A list of actions to extend.
        config_section_name: Name of the configuration section that the
            command extension will fetch configuration values from.
            Defaults to the name of the plugin in which the extension is
            defined.
    Returns:
        A wrapper object for settings.
    """

    if not actions:
        raise ValueError(
            f"argument 'actions' must be a non-empty list: {actions}"
        )
    return _CommandExtensionSettings(
        actions=actions, config_section_name=config_section_name
    )


def option(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None,
    help: str = "",
    required: bool = False,
    default: Optional[Any] = None,
    configurable: bool = False,
    converter: Optional[Callable[[str], Any]] = None,
    argparse_kwargs: Optional[Mapping[str, Any]] = None,
):
    """Create an option for a :py:class:`Command` or a
    :py:class:`CommandExtension`.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug


        class Hello(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(help="Your name.")
            age = plug.cli.option(converter=int, help="Your age.")

            def command_callback(self, args, api):
                print(
                    f"Hello, my name is {args.name} "
                    f"and I am {args.age} years old"
                )

    This command can then be called like so:

    .. code-block:: bash

        $ repobee -p ext.py hello --name Alice --age 22
        Hello, my name is Alice and I am 22 years old

    Args:
        short_name: The short name of this option. Must start with ``-``.
        long_name: The long name of this option. Must start with `--`.
        help: A description of this option that is used in the CLI help
            section.
        required: Whether or not this option is required.
        default: A default value for this option.
        configurable: Whether or not this option is configurable. If an option
            is both configurable and required, having a value for the option
            in the configuration file makes the option non-required.
        converter: A converter function that takes a string and returns
            the argument in its proper state. Should also perform input
            validation and raise an error if the input is malformed.
        argparse_kwargs: Keyword arguments that are passed directly to
            :py:meth:`argparse.ArgumentParser.add_argument`
    Returns:
        A CLI argument wrapper used internally by RepoBee to create command
        line arguments.
    """

    return _Option(
        short_name=short_name,
        long_name=long_name,
        configurable=configurable,
        help=help,
        converter=converter,
        required=required,
        default=default,
        argument_type=ArgumentType.OPTION,
        argparse_kwargs=argparse_kwargs or {},
    )


def positional(
    help: str = "",
    converter: Optional[Callable[[str], Any]] = None,
    argparse_kwargs: Optional[Mapping[str, Any]] = None,
) -> _Option:
    """Create a positional argument for a :py:class:`Command` or a
    :py:class:`CommandExtension`.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug


        class Hello(plug.Plugin, plug.cli.Command):
            name = plug.cli.Positional(help="Your name.")
            age = plug.cli.Positional(converter=int, help="Your age.")

            def command_callback(self, args, api):
                print(
                    f"Hello, my name is {args.name} "
                    f"and I am {args.age} years old"
                )

    This command can then be called like so:

    .. code-block:: bash

        $ repobee -p ext.py hello Alice 22
        Hello, my name is Alice and I am 22 years old

    Args:
        help: The help section for the positional argument.
        converter: A converter function that takes a string and returns
            the argument in its proper state. Should also perform input
            validation and raise an error if the input is malformed.
        argparse_kwargs: Keyword arguments that are passed directly to
            :py:meth:`argparse.ArgumentParser.add_argument`
    Returns:
        A CLI argument wrapper used internally by RepoBee to create command
        line argument.
    """
    return _Option(
        help=help,
        converter=converter,
        argparse_kwargs=argparse_kwargs or {},
        argument_type=ArgumentType.POSITIONAL,
    )


def mutually_exclusive_group(*, __required__: bool = False, **kwargs):
    """
    Args:
        __required__: Whether or not this mutex group is required.
        kwargs: Keyword arguments on the form ``name=plug.cli.option()``.
    """
    allowed_types = (ArgumentType.OPTION,)

    def _check_arg_type(name, opt):
        if opt.argument_type not in allowed_types:
            raise ValueError(
                f"{opt.argument_type.value} not allowed in mutex group"
            )
        return True

    options = [
        (key, value)
        for key, value in kwargs.items()
        if _check_arg_type(key, value)
    ]
    return _MutuallyExclusiveGroup(required=__required__, options=options)


_MutuallyExclusiveGroup = collections.namedtuple(
    "_MutuallyExclusiveGroup", ["options", "required"]
)


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

            name = plug.cli.option(
                short_name="-n", help="your name", required=True
            )
            age = plug.cli.option(
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
