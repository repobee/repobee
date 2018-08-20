"""config module.

Contains the code required for pre-configuring user interfaces.

.. module:: config
    :synopsis: Configuration functions and constants for pre-configuring CLI parameters.

.. moduleauthor:: Simon Larsén
"""
import pathlib
import configparser
from typing import Union
import daiquiri
import appdirs
import repomate

from repomate import exception

LOGGER = daiquiri.getLogger(__file__)

CONFIG_DIR = pathlib.Path(
    appdirs.user_config_dir(
        appname=__package__, appauthor=repomate.__author__))

DEFAULT_CONFIG_FILE = CONFIG_DIR / 'config.cnf'
assert DEFAULT_CONFIG_FILE.is_absolute()

# arguments that can be configured via config file
CONFIGURABLE_ARGS = set(('user', 'org_name', 'github_base_url',
                         'students_file'))


def get_configured_defaults(
        config_file: Union[str, pathlib.Path] = DEFAULT_CONFIG_FILE) -> dict:
    """Access the config file and return a ConfigParser instance with
    its contents.

    Args:
        config_file: Path to the config file.
    Returns:
        a dict with the contents of the config file. If there is no config
        file, the return value is an empty dict.
    """
    config_file = pathlib.Path(config_file) if isinstance(config_file,
                                                          str) else config_file
    config = _read_config(config_file)
    configured = config.keys()
    if configured - CONFIGURABLE_ARGS:  # there are surpluss arguments
        raise exception.FileError("config contains invalid keys: {}".format(
            ", ".join(configured - CONFIGURABLE_ARGS)))

    # following is logging only
    if config:
        LOGGER.info("config file defaults:\n{}".format("\n   ".join([""] + [
            "{}: {}".format(key, value) for key, value in config.items()
            if key in CONFIGURABLE_ARGS
        ] + [""])))
    else:
        LOGGER.info(
            "no config file found. Expected config file location: {!s}".format(
                DEFAULT_CONFIG_FILE))

    return config


def _read_config(config_file: pathlib.Path = DEFAULT_CONFIG_FILE) -> dict:
    if not config_file.is_file():
        return {}

    config_parser = configparser.ConfigParser()
    try:
        config_parser.read(str(config_file))
    except configparser.MissingSectionHeaderError:
        pass  # handled by the next check

    if "DEFAULTS" not in config_parser:
        raise exception.FileError(
            "config file at '{!s}' does not contain the required [DEFAULTS] header".
            format(config_file))
    return dict(config_parser["DEFAULTS"])
