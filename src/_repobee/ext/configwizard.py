"""A plugin that adds the ``config-wizard`` command to RepoBee. It runs through
a short configuration wizard that lets the user set RepoBee's defaults.

.. module:: configwizard
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import configparser
import sys

import daiquiri
import repobee_plug as plug

from _repobee import apimeta
from _repobee import constants

LOGGER = daiquiri.getLogger(__file__)


def command(args: argparse.Namespace, api: apimeta.API) -> None:
    """Run through a configuration wizard."""
    if constants.DEFAULT_CONFIG_FILE.exists():
        LOGGER.warning(
            "A configuration file was found at {}".format(
                str(constants.DEFAULT_CONFIG_FILE)
            )
        )
        LOGGER.warning(
            "Continuing this wizard will OVERWRITE your current file"
        )
        if input("Continue anyway? (yes/no): ") != "yes":
            LOGGER.info("User-prompted exit")
            return

    config = configparser.ConfigParser()
    config.add_section(constants.DEFAULTS_SECTION_HDR)

    LOGGER.info("Welcome to the configuration wizard!")
    LOGGER.info("Type defaults for the options when prompted.")
    LOGGER.info("Press ENTER to end an option.")
    LOGGER.info("Press ENTER without inputing a value to skip an option.")
    for arg in constants.ORDERED_CONFIGURABLE_ARGS:
        default = input("Default for '{}': ".format(arg))
        if default:
            config[constants.DEFAULTS_SECTION_HDR][arg] = default

    with open(
        str(constants.DEFAULT_CONFIG_FILE),
        "w",
        encoding=sys.getdefaultencoding(),
    ) as f:
        config.write(f)

    LOGGER.info(
        "Configuration file written to {}".format(
            str(constants.DEFAULT_CONFIG_FILE)
        )
    )


@plug.repobee_hook
def create_extension_command():
    parser = plug.ExtensionParser()
    return plug.ExtensionCommand(
        parser=parser,
        name="config-wizard",
        help="Config wizard",
        description="Description of config wizard",
        callback=command,
    )
