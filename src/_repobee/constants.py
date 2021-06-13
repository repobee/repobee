"""Module for constants used throughout RepoBee.


.. module:: constants
    :synopsis: Constants used throughout RepoBee.

.. moduleauthor:: Simon Larsén
"""
import pathlib

import appdirs  # type: ignore

import repobee_plug as plug

import _repobee

CONFIG_DIR = pathlib.Path(
    appdirs.user_config_dir(
        appname=_repobee._external_package_name, appauthor=_repobee.__author__
    )
)
LOCAL_CONFIG_NAME = "repobee.ini"
LOG_DIR = pathlib.Path(
    appdirs.user_log_dir(
        appname=_repobee._external_package_name, appauthor=_repobee.__author__
    )
)
MAX_LOGFILE_SIZE = 1024 * 1024 * 10  # 10 MiB
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
    plug.Config.PARENT_CONFIG_KEY,
)
CONFIGURABLE_ARGS = set(ORDERED_CONFIGURABLE_ARGS)

TOKEN_ENV = "REPOBEE_TOKEN"
