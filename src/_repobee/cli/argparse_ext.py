"""RepoBee extensions of argparse."""
import argparse
import dataclasses

from typing import Optional

from _repobee import constants

__all__ = [
    "RepobeeParser",
    "OrderedFormatter",
    "BaseParsers",
    "add_debug_args",
    "CATEGORY_DEST",
    "ACTION_DEST",
]

CATEGORY_DEST = "category"
ACTION_DEST = "action"


@dataclasses.dataclass
class BaseParsers:
    base_parser: argparse.ArgumentParser
    student_parser: argparse.ArgumentParser
    template_org_parser: argparse.ArgumentParser
    repo_name_parser: argparse.ArgumentParser
    repo_discovery_parser: argparse.ArgumentParser


class RepobeeParser(argparse.ArgumentParser):
    """A thin wrapper around :py:class:`argparse.ArgumentParser`. The primary
    functionality of this class is to group the core CLI arguments into
    argument groups such that the CLI doesn't get too cluttered.
    """

    def __init__(self, *args, is_core_command: bool = False, **kwargs):
        self._is_core_command = is_core_command
        super().__init__(*args, **kwargs)
        self._platform_args_grp = self.add_argument_group(
            title="platform arguments",
            description="Arguments related to the platform "
            "(e.g. GitHub or GitLab)",
        )
        self._debug_args_grp = self.add_argument_group(title="debug arguments")
        self._alpha_args_grp = self.add_argument_group(
            title="alpha arguments",
            description="Arguments that are currently being trialed in alpha, "
            "and may change without further notice",
        )

    def add_argument(self, *args, **kwargs):
        """Add an argument to this parser, placing it in an appropriate
        argument group.
        """
        if not self._is_core_command:
            return super().add_argument(*args, **kwargs)

        platform_args = {
            "--token",
            "--org-name",
            "--template-org-name",
            "--user",
            "--base-url",
        }
        debug_args = {"--traceback", "--quiet", "--verbose"}
        alpha_args = {"--hook-results-file", "--double-blind-key"}

        for arg in args:
            if arg in platform_args:
                return self._platform_args_grp.add_argument(*args, **kwargs)
            elif arg in debug_args:
                return self._debug_args_grp.add_argument(*args, **kwargs)
            elif arg in alpha_args:
                return self._alpha_args_grp.add_argument(*args, **kwargs)

        return super().add_argument(*args, **kwargs)

    def add_argument_group(  # type: ignore
        self, title: Optional[str] = None, description: Optional[str] = None
    ) -> argparse._ArgumentGroup:
        """Create a new argument group if the title does not exist, or return
        an existing one if it does.
        """
        for grp in self._action_groups:
            if grp.title == title:
                if description is not None:
                    grp.description = description
                return grp
        return super().add_argument_group(title, description)


class OrderedFormatter(argparse.HelpFormatter):
    """A formatter class for putting out the help section in a proper order.
    All of the arguments that are configurable in the configuration file
    should appear at the bottom (in arbitrary, but always the same, order).
    Any other arguments should appear in the order they are added.

    The internals of the formatter classes are technically not public,
    so this class is "unsafe" when it comes to new versions of Python. It may
    have to be disabled for future versions, but it works for 3.6, 3.7 and 3.8
    at the time of writing. If this turns troublesome, it may be time to
    switch to some other CLI library.
    """

    def add_arguments(self, actions):
        """Order actions by the name  of the long argument, and then add them
        as arguments.

        The order is the following:

        [ NON-CONFIGURABLE | CONFIGURABLE | DEBUG ]

        Non-configurable arguments added without modification, which by
        default is the order they are added to the parser. Configurable
        arguments are added in the order defined by
        :py:const:`constants.ORDERED_CONFIGURABLE_ARGS`. Finally, debug
        commands (such as ``--traceback``) are added in arbitrary (but
        consistent) order.
        """
        args_order = tuple(
            "--" + name.replace("_", "-")
            for name in constants.ORDERED_CONFIGURABLE_ARGS
        ) + ("--traceback",)

        def key(action):
            if len(action.option_strings) < 2:
                return -1
            long_arg = action.option_strings[1]
            if long_arg in args_order:
                return args_order.index(long_arg)
            return -1

        actions = sorted(actions, key=key)
        super().add_arguments(actions)


def add_debug_args(parser: argparse.ArgumentParser) -> None:
    """Add RepoBee's standard debug arguments to this parser.

    Args:
        parser: A parser to add arguments to.
    """
    parser.add_argument(
        "--tb",
        "--traceback",
        help="show the full traceback of critical exceptions",
        action="store_true",
        dest="traceback",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="silence output (stacks up to 3 times: -q=only warnings "
        "and errors, -qq=only errors, -qqq=complete and utter silence)",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase verbosity of output (stacks up to 2 times: "
        "-v=info logging, -vv=debug logging",
        action="count",
        default=0,
    )
