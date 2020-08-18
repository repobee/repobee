"""Module for constants used throughout RepoBee.


.. module:: constants
    :synopsis: Constants used throughout RepoBee.

.. moduleauthor:: Simon Larsén
"""
import pathlib

import appdirs

import _repobee

CONFIG_DIR = pathlib.Path(
    appdirs.user_config_dir(
        appname=_repobee._external_package_name, appauthor=_repobee.__author__
    )
)
LOG_DIR = pathlib.Path(
    appdirs.user_log_dir(
        appname=_repobee._external_package_name, appauthor=_repobee.__author__
    )
)
CORE_SECTION_HDR = "repobee"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "config.ini"
assert DEFAULT_CONFIG_FILE.is_absolute()

# arguments that can be configured via config file
ORDERED_CONFIGURABLE_ARGS = (
    "user",
    "base_url",
    "org_name",
    "template_org_name",
    "token",
    "students_file",
    "plugins",
)
CONFIGURABLE_ARGS = set(ORDERED_CONFIGURABLE_ARGS)

TOKEN_ENV = "REPOBEE_TOKEN"
