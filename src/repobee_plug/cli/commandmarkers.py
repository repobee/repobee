"""Mixin classes for marking plugins as CLI commands/extensions."""

import argparse


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
    an extension command.

    An extension command must have an callback defined in the class on the
    following form:

    .. code-block:: python

        def command(
            self, args: argparse.Namespace, api: plug.API
        ) -> Optional[plug.Result]:
            pass

    Note that the type hints are not required, so the callback can be defined
    like this instead:

    .. code-block:: python

        def command(self, args, api):
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

            def command(self, args, api):
                print(f"Hello, my name is {args.name} and I am {args.age}")

    Note that the file is called ``command.py``. We can run this command with
    RepoBee like so:

    .. code-block:: bash

        $ repobee -p command.py greeting -n Alice
        Hello, my name is Alice and I am 30
    """

    args: argparse.Namespace

    def __getattr__(self, key):
        """We implement getattr such that linters won't complain about
        dynamically added members.
        """
        return object.__getattribute__(self, key)
