"""config module.

Contains the code required for pre-configuring user interfaces.

.. module:: config
    :synopsis: Configuration functions and constants for pre-configuring CLI parameters.

.. moduleauthor:: Simon Larsén
"""
import os
import pathlib
import configparser
from typing import Union, List, Mapping
import daiquiri
import appdirs
import repomate

from repomate import exception

import repomate_plug as plug

LOGGER = daiquiri.getLogger(__file__)

CONFIG_DIR = pathlib.Path(
    appdirs.user_config_dir(
        appname=__package__, appauthor=repomate.__author__))

DEFAULTS_SECTION_HDR = 'DEFAULTS'
DEFAULT_CONFIG_FILE = CONFIG_DIR / 'config.cnf'
assert DEFAULT_CONFIG_FILE.is_absolute()

# arguments that can be configured via config file
CONFIGURABLE_ARGS = set(('user', 'org_name', 'github_base_url',
                         'students_file', 'plugins'))


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
    config_file = pathlib.Path(config_file)
    defaults = _read_defaults(config_file)
    check_defaults(defaults)
    return defaults


def check_defaults(defaults: Mapping[str, str]):
    """Raise an exception if defaults contain keys that are not configurable
    arguments.

    Args:
        defaults: A dictionary of defaults.
    """
    configured = defaults.keys()
    if configured - CONFIGURABLE_ARGS:  # there are surpluss arguments
        raise exception.FileError(
            "config contains invalid default keys: {}".format(
                ", ".join(configured - CONFIGURABLE_ARGS)))


def get_plugin_names(
        config_file: Union[str, pathlib.Path] = DEFAULT_CONFIG_FILE
) -> List[str]:
    """Return a list of unqualified names of plugins listed in the config. The
    order of the plugins is preserved.

    Args:
        config_file: path to the config file.

    Returns:
        a list of unqualified names of plugin modules, or an empty list if no
        plugins are listed.
    """
    config_file = pathlib.Path(config_file) if isinstance(config_file,
                                                          str) else config_file
    if not config_file.is_file():
        return []
    config = _read_config(config_file)
    plugin_string = config.get(DEFAULTS_SECTION_HDR, 'plugins', fallback="")
    return [name.strip() for name in plugin_string.split(",") if name]


def execute_config_hooks(
        config_file: Union[str, pathlib.Path] = DEFAULT_CONFIG_FILE) -> None:
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
        config_file: Union[str, pathlib.Path] = DEFAULT_CONFIG_FILE) -> None:
    """Raise an exception if the configuration file contains syntactical
    errors, or if the defaults are misconfigured. Note that plugin options are
    not checked.

    Args:
        config_file: path to the config file.
    """
    config_file = pathlib.Path(config_file)
    if not config_file.is_file():
        raise exception.FileError("no config file found, expected location: " +
                                  str(config_file))

    try:
        defaults = _read_defaults(config_file)
    except configparser.ParsingError as exc:
        errors = ', '.join("(line {}: {})".format(line_nr, line)
                           for line_nr, line in exc.errors)
        raise exception.FileError(
            msg="config file contains syntax errors: " + errors)
    check_defaults(defaults)


def _read_defaults(config_file: pathlib.Path = DEFAULT_CONFIG_FILE) -> dict:
    if not config_file.is_file():
        return {}
    return dict(_read_config(config_file)[DEFAULTS_SECTION_HDR])


def _read_config(config_file: pathlib.Path = DEFAULT_CONFIG_FILE
                 ) -> configparser.ConfigParser:
    config_parser = configparser.ConfigParser()
    try:
        config_parser.read(str(config_file))
    except configparser.MissingSectionHeaderError:
        pass  # handled by the next check

    if DEFAULTS_SECTION_HDR not in config_parser:
        raise exception.FileError(
            "config file at '{!s}' does not contain the required [DEFAULTS] header"
            .format(config_file))

    return config_parser
