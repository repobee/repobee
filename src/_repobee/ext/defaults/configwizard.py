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

import repobee_plug as plug

from _repobee import constants


class Wizard(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        category=plug.cli.CoreCommand.config,
        help="Interactive configuration wizard to set up the config file.",
        description=(
            "A configuration wizard that sets up the configuration file."
            "Warns if there already is a configuration file, as it will be "
            "overwritten."
        ),
    )

    def command(self, api: plug.PlatformAPI) -> None:
        return callback(self.args, api)


def callback(args: argparse.Namespace, api: plug.PlatformAPI) -> None:
    """Run through a configuration wizard."""
    parser = configparser.ConfigParser()

    if constants.DEFAULT_CONFIG_FILE.exists():
        plug.log.warning(
            "A configuration file was found at {}".format(
                str(constants.DEFAULT_CONFIG_FILE)
            )
        )
        plug.log.warning(
            "Continuing this wizard will OVERWRITE any options you enter "
            "values for"
        )
        if input("Continue anyway? (yes/no): ") != "yes":
            plug.echo("User-prompted exit")
            return
        parser.read(str(constants.DEFAULT_CONFIG_FILE))

    os.makedirs(
        str(constants.DEFAULT_CONFIG_FILE.parent), mode=0o700, exist_ok=True
    )
    if constants.CORE_SECTION_HDR not in parser:
        parser.add_section(constants.CORE_SECTION_HDR)

    plug.echo("Welcome to the configuration wizard!")
    plug.echo("Type defaults for the options when prompted.")
    plug.echo("Press ENTER to end an option.")
    plug.echo(
        "Press ENTER without inputing a value to pick existing "
        "default, or skip if no default exists."
    )
    plug.echo("Current defaults are shown in brackets [].")
    for option in constants.ORDERED_CONFIGURABLE_ARGS:
        prompt = "Enter default for '{}': [{}] ".format(
            option, parser[constants.CORE_SECTION_HDR].get(option, "")
        )
        default = input(prompt)
        if default:
            parser[constants.CORE_SECTION_HDR][option] = default

    with open(
        str(constants.DEFAULT_CONFIG_FILE),
        "w",
        encoding=sys.getdefaultencoding(),
    ) as f:
        parser.write(f)

    plug.echo(
        "Configuration file written to {}".format(
            str(constants.DEFAULT_CONFIG_FILE)
        )
    )
