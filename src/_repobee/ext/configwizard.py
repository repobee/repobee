"""A plugin that adds the ``config-wizard`` command to RepoBee. It runs through
a short configuration wizard that lets the user set RepoBee's defaults.

.. module:: configwizard
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import configparser
import sys
import os

import daiquiri
import repobee_plug as plug

from _repobee import constants

LOGGER = daiquiri.getLogger(__file__)


def callback(args: argparse.Namespace, api: plug.API) -> None:
    """Run through a configuration wizard."""
    parser = configparser.ConfigParser()

    if constants.DEFAULT_CONFIG_FILE.exists():
        LOGGER.warning(
            "A configuration file was found at {}".format(
                str(constants.DEFAULT_CONFIG_FILE)
            )
        )
        LOGGER.warning(
            "Continuing this wizard will OVERWRITE any options you enter "
            "values for"
        )
        if input("Continue anyway? (yes/no): ") != "yes":
            LOGGER.info("User-prompted exit")
            return
        parser.read(str(constants.DEFAULT_CONFIG_FILE))

    os.makedirs(
        str(constants.DEFAULT_CONFIG_FILE.parent), mode=0o700, exist_ok=True
    )
    if constants.DEFAULTS_SECTION_HDR not in parser:
        parser.add_section(constants.DEFAULTS_SECTION_HDR)

    LOGGER.info("Welcome to the configuration wizard!")
    LOGGER.info("Type defaults for the options when prompted.")
    LOGGER.info("Press ENTER to end an option.")
    LOGGER.info(
        "Press ENTER without inputing a value to pick existing "
        "default, or skip if no default exists."
    )
    LOGGER.info("Current defaults are shown in brackets [].")
    for option in constants.ORDERED_CONFIGURABLE_ARGS:
        prompt = "Enter default for '{}': [{}] ".format(
            option, parser[constants.DEFAULTS_SECTION_HDR].get(option, "")
        )
        default = input(prompt)
        if default:
            parser[constants.DEFAULTS_SECTION_HDR][option] = default

    with open(
        str(constants.DEFAULT_CONFIG_FILE),
        "w",
        encoding=sys.getdefaultencoding(),
    ) as f:
        parser.write(f)

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
        help="Interactive configuration wizard to set up the config file.",
        description=(
            "A configuration wizard that sets up the configuration file."
            "Warns if there already is a configuration file, as it will be "
            "overwritten."
        ),
        callback=callback,
    )
