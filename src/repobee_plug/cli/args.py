"""Command line options for extension commands."""
import collections
import enum
from typing import Optional, Any, Callable, Mapping


class ArgumentType(enum.Enum):
    OPTION = "Option"
    POSITIONAL = "Positional"
    MUTEX_GROUP = "Mutex"


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
        "argument_type",
        "argparse_kwargs",
    ],
)
Option.__new__.__defaults__ = (None,) * len(Option._fields)

MutuallyExclusiveGroup = collections.namedtuple(
    "MutuallyExclusiveGroup", ["options", "required"]
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

            def command(self, args, api):
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
            name = plug.cli.Positional(help="Your name.")
            age = plug.cli.Positional(converter=int, help="Your age.")

            def command(self, args, api):
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
    return Option(
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
    return MutuallyExclusiveGroup(required=__required__, options=options)
