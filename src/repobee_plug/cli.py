"""Plugin functionality for creating extensions to the RepoBee CLI."""
import collections

__all__ = ["Option", "Action"]


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


class Action:
    """Mixin class for use with the Plugin class. Explicitly marks a class as a
    CLI Action.

    Example usage:

    .. code-block:: python

        import repobee_plug as plug

        class Greeting(plug.Plugin, plug.cli.Action):

            name = plug.cli.Option(
                short_name="-n", help="your name", required=True
            )
            age = plug.cli.Option(
                converter=int, help="your age", default=30
            )

            def cli_callback(self, args, api):
                print(f"Hello, my name is {args.name} and I am {args.age}")
    """
