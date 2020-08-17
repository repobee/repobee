"""Command line options for extension commands."""
import dataclasses
import enum
from typing import Optional, Any, Callable, Mapping, List, Tuple


class ArgumentType(enum.Enum):
    OPTION = "option"
    POSITIONAL = "positional"
    MUTEX_GROUP = "mutually_exclusive_group"
    FLAG = "flag"


@dataclasses.dataclass(frozen=True)
class Option:
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    configurable: Optional[bool] = None
    help: Optional[str] = None
    converter: Optional[Callable[[str], Any]] = None
    required: Optional[bool] = None
    default: Optional[Any] = None
    argument_type: ArgumentType = ArgumentType.OPTION
    argparse_kwargs: Optional[Mapping[str, Any]] = None


@dataclasses.dataclass(frozen=True)
class MutuallyExclusiveGroup:
    options: List[Tuple[str, Option]]
    required: bool = False

    def __post_init__(self):
        for name, opt in self.options:
            self._check_arg_type(name, opt)

    def _check_arg_type(self, name: str, opt: Option):
        allowed_types = (ArgumentType.OPTION, ArgumentType.FLAG)

        if opt.argument_type not in allowed_types:
            raise ValueError(
                f"{opt.argument_type.value} not allowed in mutex group"
            )


def is_cli_arg(obj: Any) -> bool:
    """Determine if an object is a CLI argument.

    Args:
        obj: An object.
    Returns:
        True if the object is an instance of a CLI argument class.
    """
    return isinstance(obj, (Option, MutuallyExclusiveGroup))


def option(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None,
    help: str = "",
    required: bool = False,
    default: Optional[Any] = None,
    configurable: bool = False,
    converter: Optional[Callable[[str], Any]] = None,
    argparse_kwargs: Optional[Mapping[str, Any]] = None,
) -> Option:
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

    return Option(
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
) -> Option:
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
    return Option(
        help=help,
        converter=converter,
        argparse_kwargs=argparse_kwargs or {},
        argument_type=ArgumentType.POSITIONAL,
    )


def flag(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None,
    help: str = "",
    const: Any = True,
    default: Optional[Any] = None,
) -> Option:
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
    return Option(
        short_name=short_name,
        long_name=long_name,
        help=help,
        argparse_kwargs=dict(
            action="store_const", const=const, default=resolved_default
        ),
        argument_type=ArgumentType.FLAG,
    )


def mutually_exclusive_group(*, __required__: bool = False, **kwargs):
    """
    Args:
        __required__: Whether or not this mutex group is required.
        kwargs: Keyword arguments on the form ``name=plug.cli.option()``.
    """
    options = [(key, value) for key, value in kwargs.items()]
    return MutuallyExclusiveGroup(required=__required__, options=options)
