from .settings import command_settings, command_extension_settings
from .categorization import category
from .args import (
    option,
    positional,
    flag,
    mutually_exclusive_group,
    ArgumentType,
    is_cli_arg,
)
from .commandmarkers import Command, CommandExtension

from ._corecommand import _CoreCommand

CoreCommand = _CoreCommand()

__all__ = [
    "ArgumentType",
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
    "is_cli_arg",
]
