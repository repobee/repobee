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
from typing import Union, List, Mapping, Optional

import daiquiri
import repobee_plug as plug

from _repobee import exception
from _repobee import constants


LOGGER = daiquiri.getLogger(__file__)


def get_configured_defaults(
    config_file: Union[str, pathlib.Path] = constants.DEFAULT_CONFIG_FILE
) -> dict:
    """Access the config file and return a ConfigParser instance with
    its contents.

    Args:
        config_file: Path to the config file.
    Returns:
        a dict with the contents of the config file. If there is no config
        file, the return value is an empty dict.
    """
    config_file = pathlib.Path(config_file)
    defaults = _read_defaults(config_file)
    check_defaults(defaults, config_file)
    return defaults


def check_defaults(
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
            "config file at {} contains invalid default keys: {}".format(
                config_file,
                ", ".join(configured - constants.CONFIGURABLE_ARGS),
            )
        )


def get_plugin_names(
    config_file: Union[str, pathlib.Path] = constants.DEFAULT_CONFIG_FILE
) -> List[str]:
    """Return a list of unqualified names of plugins listed in the config. The
    order of the plugins is preserved.

    Args:
        config_file: path to the config file.

    Returns:
        a list of unqualified names of plugin modules, or an empty list if no
        plugins are listed.
    """
    config_file = (
        pathlib.Path(config_file)
        if isinstance(config_file, str)
        else config_file
    )
    if not config_file.is_file():
        return []
    config = _read_config(config_file)
    plugin_string = config.get(
        constants.DEFAULTS_SECTION_HDR, "plugins", fallback=""
    )
    return [name.strip() for name in plugin_string.split(",") if name]


def execute_config_hooks(
    config_file: Union[str, pathlib.Path] = constants.DEFAULT_CONFIG_FILE
) -> None:
    """Execute all config hooks.

    Args:
        config_file: path to the config file.
    """
    config_file = pathlib.Path(config_file)
    if not config_file.is_file():
        return
    config_parser = _read_config(config_file)
    plug.manager.hook.config_hook(config_parser=config_parser)


def check_config_integrity(
    config_file: Union[str, pathlib.Path] = constants.DEFAULT_CONFIG_FILE
) -> None:
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
            "(line {}: {})".format(line_nr, line)
            for line_nr, line in exc.errors
        )
        raise exception.FileError(
            msg="config file at {} contains syntax errors: {}".format(
                config_file, errors
            )
        )
    check_defaults(defaults, config_file)


def get_all_tasks() -> List[plug.Task]:
    """Return all plugin tasks, regardless of which command they are intended for.

    Returns:
        All plugin tasks.
    """
    return plug.manager.hook.setup_task() + plug.manager.hook.clone_task()


def _fetch_token() -> Optional[str]:
    token = os.getenv(constants.TOKEN_ENV)
    token_from_old = os.getenv(constants.TOKEN_ENV_OLD)
    if token_from_old:
        LOGGER.warning(
            "The {} environment variable has been deprecated, "
            "use {} instead".format(
                constants.TOKEN_ENV_OLD, constants.TOKEN_ENV
            )
        )
    return token or token_from_old


def _read_defaults(
    config_file: pathlib.Path = constants.DEFAULT_CONFIG_FILE,
) -> dict:
    token = _fetch_token()
    if not config_file.is_file():
        return {} if not token else dict(token=token)
    defaults = dict(_read_config(config_file)[constants.DEFAULTS_SECTION_HDR])
    if token:
        if defaults.get("token"):
            LOGGER.warning(
                "REPOBEE_TOKEN environment variable overrides token in "
                "config file"
            )
        defaults["token"] = token
    return defaults


def _read_config(
    config_file: pathlib.Path = constants.DEFAULT_CONFIG_FILE,
) -> configparser.ConfigParser:
    config_parser = configparser.ConfigParser()
    try:
        config_parser.read(str(config_file))
    except configparser.MissingSectionHeaderError:
        pass  # handled by the next check

    if constants.DEFAULTS_SECTION_HDR not in config_parser:
        raise exception.FileError(
            "config file at '{!s}' does not contain the required "
            "[DEFAULTS] header".format(config_file)
        )

    return config_parser
