from repobee_plug.cli.settings import (
    command_settings,
    command_extension_settings,
)
from repobee_plug.cli.categorization import category
from repobee_plug.cli.args import (
    option,
    positional,
    flag,
    mutually_exclusive_group,
    is_cli_arg,
)
from repobee_plug.cli.commandmarkers import Command, CommandExtension

from repobee_plug.cli.base import _CoreCommand
from repobee_plug.cli.base import BaseParser

CoreCommand = _CoreCommand()

__all__ = [
    "option",
    "positional",
    "flag",
    "mutually_exclusive_group",
    "category",
    "command_settings",
    "command_extension_settings",
    "Command",
    "CommandExtension",
    "CoreCommand",
    "BaseParser",
    "is_cli_arg",
]
