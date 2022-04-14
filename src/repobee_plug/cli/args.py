"""Command line options for extension commands."""
import dataclasses
import enum
from typing import Optional, Any, Callable, Mapping, List, Tuple


class _ArgumentType(enum.Enum):
    OPTION = "option"
    POSITIONAL = "positional"
    MUTEX_GROUP = "mutually_exclusive_group"
    FLAG = "flag"
    # for one reason or another, this argument should be ignored when adding
    # arguments to the parser. This is typically used by mutex groups to add
    # their arguments to the top level of the class
    IGNORE = "ignore"


class _NotSet:
    """A marker to indicate that a value is not set."""

    def __repr__(self):
        return "_NotSet()"

    def __str__(self):
        return "The value related to this argument has not yet been set"


NOTSET = _NotSet()


@dataclasses.dataclass
class _Option:
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    configurable: Optional[bool] = None
    help: Optional[str] = None
    converter: Optional[Callable[[str], Any]] = None
    required: Optional[bool] = None
    default: Optional[Any] = None
    argument_type: _ArgumentType = _ArgumentType.OPTION
    argparse_kwargs: Optional[Mapping[str, Any]] = None
    # Value_attr_name should be set by the __set_name__ function. Attempting to
    # use this default will cause a crash as it isn't a valid Python identifier
    value_attr_name: str = "invalid attribute name"

    def __set_name__(self, owner, name) -> None:
        if self.long_name is None:
            self.long_name = f"--{name.replace('_', '-')}"
        self.value_attr_name = f"_parsed_value_{name}"

    def __set__(self, obj, value) -> None:
        setattr(obj, self.value_attr_name, value)

    def __get__(self, obj, type=None) -> Any:
        return getattr(obj, self.value_attr_name, NOTSET)


@dataclasses.dataclass(frozen=True)
class _MutuallyExclusiveGroup:
    options: List[Tuple[str, _Option]]
    required: bool = False

    def __post_init__(self):
        for name, opt in self.options:
            self._check_arg_type(name, opt)
            # __set_name__ must be called explicitly as it is not called when
            # assigning values to keyword arguments, as is done in mutex groups
            opt.__set_name__(self, name)

    def _check_arg_type(self, name: str, opt: _Option):
        allowed_types = (_ArgumentType.OPTION, _ArgumentType.FLAG)

        if opt.argument_type not in allowed_types:
            raise ValueError(
                f"{opt.argument_type.value} not allowed in mutex group"
            )

    def __set__(self, obj, value) -> None:
        self._add_options_to_obj(obj, self.options)

    @staticmethod
    def _add_options_to_obj(
        obj: object, options: List[Tuple[str, _Option]]
    ) -> None:
        for name, opt in options:
            setattr(
                obj,
                name,
                dataclasses.replace(opt, argument_type=_ArgumentType.IGNORE),
            )


def is_cli_arg(obj: Any) -> bool:
    """Determine if an object is a CLI argument.

    Args:
        obj: An object.
    Returns:
        True if the object is an instance of a CLI argument class.
    """
    return isinstance(obj, (_Option, _MutuallyExclusiveGroup))


def option(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None,
    help: str = "",
    required: bool = False,
    default: Optional[Any] = None,
    configurable: bool = False,
    converter: Optional[Callable[[str], Any]] = None,
    argparse_kwargs: Optional[Mapping[str, Any]] = None,
) -> _Option:
    """Create an option for a :py:class:`Command` or a
    :py:class:`CommandExtension`.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug


        class Hello(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(help="Your name.")
            age = plug.cli.option(converter=int, help="Your age.")

            def command(self):
                print(
                    f"Hello, my name is {self.name} "
                    f"and I am {self.age} years old"
                )

    This command can then be called like so:

    .. code-block:: bash

        $ repobee -p ext.py hello --name Alice --age 22
        Hello, my name is Alice and I am 22 years old

    .. danger::

        This function returns an `_Option`, which is an internal structure. You
        should not handle this value directly, it should only ever be assigned
        as an attribute to a command class.

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
        argument_type=_ArgumentType.OPTION,
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
            name = plug.cli.positional(help="Your name.")
            age = plug.cli.positional(converter=int, help="Your age.")

            def command(self):
                print(
                    f"Hello, my name is {self.name} "
                    f"and I am {self.age} years old"
                )

    This command can then be called like so:

    .. code-block:: bash

        $ repobee -p ext.py hello Alice 22
        Hello, my name is Alice and I am 22 years old

    .. danger::

        This function returns an `_Option`, which is an internal structure. You
        should not handle this value directly, it should only ever be assigned
        as an attribute to a command class.

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
        argument_type=_ArgumentType.POSITIONAL,
    )


def flag(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None,
    help: str = "",
    const: Any = True,
    default: Optional[Any] = None,
) -> _Option:
    """Create a command line flag for a :py:class:`Command` or a
    :py:class`CommandExtension`. This is simply a convenience wrapper around
    :py:func:`option`.

    A flag is specified on the command line as ``--flag``, and causes a
    constant to be stored. If the flag is omitted, a default value is used
    instead. The default behavior is that specifying ``--flag``
    stores the constant ``True``, and omitting it causes it to default to
    ``False``. It can also be used to store any other form of constant by
    specifying the ``const`` argument. If so, then omitting the flag will cause
    it to default to ``None`` instead of ``False``. Finally, the default value
    can also be overridden by specifying the ``default`` argument.

    Example:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug


        class Flags(plug.Plugin, plug.cli.Command):
            # a normal flag, which toggles between True and False
            is_great = plug.cli.flag()
            # a "reverse" flag which defaults to True instead of False
            not_great = plug.cli.flag(const=False, default=True)
            # a flag that stores a constant and defaults to None
            meaning = plug.cli.flag(const=42)
            # a flag that stores a constant and defaults to another constant
            approve = plug.cli.flag(const="yes", default="no")

            def command(self):
                print("is_great", self.is_great)
                print("not_great", self.not_great)
                print("meaning", self.meaning)
                print("approve", self.approve)

    We can then call this command (for example) like so:

        .. code-block:: bash

            $ repobee -p ext.py flags --meaning --not-great
            is_great False
            not_great False
            meaning 42
            approve no

    .. danger::

        This function returns an `_Option`, which is an internal structure. You
        should not handle this value directly, it should only ever be assigned
        as an attribute to a command class.

    Args:
        short_name: The short name of this option. Must start with ``-``.
        long_name: The long name of this option. Must start with `--`.
        help: A description of this option that is used in the CLI help
            section.
        const: The constant to store.
        default: The value to default to if the flag is omitted.
    Returns:
        A CLI argument wrapper used internally by RepoBee to create command
        line argument.
    """
    resolved_default = (
        not const if default is None and isinstance(const, bool) else default
    )
    return _Option(
        short_name=short_name,
        long_name=long_name,
        help=help,
        argparse_kwargs=dict(
            action="store_const", const=const, default=resolved_default
        ),
        argument_type=_ArgumentType.FLAG,
    )


def mutually_exclusive_group(*, __required__: bool = False, **kwargs):
    """Create a mutually exclusive group of arguments in a command.

    .. danger::

        This function returns a `_MutuallyExclusiveGroup`, which is an internal
        structure. You should not handle this value directly, it should only
        ever be assigned as an attribute to a command class.

    Args:
        __required__: Whether or not this mutex group is required.
        kwargs: Keyword arguments on the form ``name=plug.cli.option()``.
    """
    num_configurable = sum(
        option.configurable or 0 for option in kwargs.values()
    )
    if num_configurable > 1:
        raise ValueError(
            f"at most 1 option in a mutex group can be configurable, found "
            f"{num_configurable}"
        )

    return _MutuallyExclusiveGroup(
        required=__required__, options=list(kwargs.items())
    )


@dataclasses.dataclass(frozen=True)
class ConfigurableArguments:
    """A container for holding a plugin's configurable arguments."""

    config_section_name: str
    argnames: List[str]
