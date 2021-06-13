"""config module.

Contains the code required for pre-configuring user interfaces.

.. module:: config
    :synopsis: Configuration functions and constants for pre-configuring CLI
        parameters.

.. moduleauthor:: Simon Larsén
"""
import os
import pathlib
import configparser
from typing import Union, Mapping

import repobee_plug as plug

from _repobee import exception
from _repobee import constants


def _check_defaults(
    defaults: Mapping[str, str], config_file: Union[str, pathlib.Path]
):
    """Raise an exception if defaults contain keys that are not configurable
    arguments.

    Args:
        defaults: A dictionary of defaults.
        config_file: Path to the config file.
    """
    configured = defaults.keys()
    if (
        configured - constants.CONFIGURABLE_ARGS
    ):  # there are surpluss arguments
        raise exception.FileError(
            f"config file at {config_file} contains invalid default keys: "
            f"{', '.join(configured - constants.CONFIGURABLE_ARGS)}"
        )


def execute_config_hooks(config: plug.Config) -> None:
    """Execute all config hooks.

    Args:
        config: The current configuration.
    """
    plug.manager.hook.handle_config(config=config)
    if not config.path.is_file():
        return
    config_parser = _read_config(config.path)
    plug.manager.hook.config_hook(
        config_parser=config_parser
    )  # TODO remove by 3.8.0


def check_config_integrity(config_file: Union[str, pathlib.Path]) -> None:
    """Raise an exception if the configuration file contains syntactical
    errors, or if the defaults are misconfigured. Note that plugin options are
    not checked.

    Args:
        config_file: path to the config file.
    """
    config_file = pathlib.Path(config_file)
    if not config_file.is_file():
        raise exception.FileError(
            "no config file found, expected location: " + str(config_file)
        )

    try:
        defaults = _read_defaults(config_file)
    except configparser.ParsingError as exc:
        errors = ", ".join(
            f"(line {line_nr}: {line})" for line_nr, line in exc.errors
        )
        raise exception.FileError(
            msg=(
                f"config file at {config_file} contains syntax errors: "
                f"{errors}"
            )
        )
    _check_defaults(defaults, config_file)


def _read_defaults(config_file: pathlib.Path) -> dict:
    token = os.getenv(constants.TOKEN_ENV)
    if not config_file.is_file():
        return {} if not token else dict(token=token)
    defaults = dict(_read_config(config_file)[plug.Config.CORE_SECTION_NAME])
    if token:
        if defaults.get("token"):
            plug.log.warning(
                "REPOBEE_TOKEN environment variable overrides token in "
                "config file"
            )
        defaults["token"] = token
    return defaults


def _read_config(config_file: pathlib.Path) -> configparser.ConfigParser:
    config_parser = configparser.ConfigParser()
    try:
        config_parser.read(str(config_file))
    except configparser.MissingSectionHeaderError:
        pass  # handled by the next check

    if plug.Config.CORE_SECTION_NAME not in config_parser:
        raise exception.FileError(
            f"config file at '{str(config_file)}' does not contain the "
            f"required [repobee] header"
        )

    return config_parser
