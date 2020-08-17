"""Mixin classes for marking plugins as CLI commands/extensions."""

import argparse
import inspect


class CommandExtension:
    """Mixin class for use with the Plugin class. Marks the extending class as
    a command extension, that adds options to an existing command.
    """

    args: argparse.Namespace

    def __getattr__(self, key):
        """We implement getattr such that linters won't complain about
        dynamically added members.
        """
        return object.__getattribute__(self, key)


class Command:
    """Mixin class for use with the Plugin class. Explicitly marks a class as
    a plugin command.

    A plugin command must have a command function defined in the class on the
    following form:

    .. code-block:: python

        def command(self) -> Optional[plug.Result]:
            pass

    Note that the type hints are not required, so the callback can be defined
    like this instead:

    .. code-block:: python

        def command(self):
            pass

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

            def command(self):
                print(f"Hello, my name is {self.name} and I am {self.age}")

    Note that the file is called ``command.py``. We can run this command with
    RepoBee like so:

    .. code-block:: bash

        $ repobee -p command.py greeting -n Alice
        Hello, my name is Alice and I am 30

    If your command requires the platform api, simply add an argument called
    ``api`` to the ``command`` function.

    .. code-block:: python
        :caption: Command function that requires the platform API

        def command(self, api: plug.PlatformAPI):
            pass

    """

    args: argparse.Namespace

    def __getattr__(self, key):
        """We implement getattr such that linters won't complain about
        dynamically added members.
        """
        return object.__getattribute__(self, key)

    def __requires_api__(self) -> bool:
        """Returns ``True`` if this command requires the platform API."""
        return "api" in inspect.signature(self.command).parameters
