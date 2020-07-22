"""Plugin functionality for creating extensions to the RepoBee CLI."""
import collections
from typing import List, Tuple

from repobee_plug import _containers

__all__ = [
    "Option",
    "Positional",
    "MutuallyExclusiveGroup",
    "Command",
    "CommandExtension",
]


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

    def __init__(self, *, required: bool = False, **kwargs):
        """
        Args:
            required: Whether or not this mutex group is required.
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
        object.__setattr__(self, "required", required)


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
