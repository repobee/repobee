"""A plugin that adds the ``config-wizard`` command to RepoBee. It runs through
a short configuration wizard that lets the user set RepoBee's defaults.

.. module:: configwizard
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import configparser
import collections
import os

import bullet

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

    def command(self) -> None:
        return callback(self.args)


def callback(args: argparse.Namespace) -> None:
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

    configurable_args = [
        plug.ConfigurableArguments(
            config_section_name=constants.CORE_SECTION_HDR,
            argnames=list(constants.ORDERED_CONFIGURABLE_ARGS),
        )
    ] + plug.manager.hook.get_configurable_args()

    configurable_args_dict = collections.defaultdict(list)
    for ca in configurable_args:
        configurable_args_dict[ca.config_section_name] += ca.argnames

    section = bullet.Bullet(
        prompt="Select a section to configure:",
        choices=list(configurable_args_dict.keys()),
    ).launch()

    plug.echo("")
    plug.echo(
        f"""Configuring section: {section}
Type config values for the options when prompted.
Press ENTER without inputing a value to pick existing default.

Current defaults are shown in brackets [].
"""
    )
    for option in configurable_args_dict[section]:
        prompt = "Enter default for '{}': [{}] ".format(
            option, parser.get(section, option, fallback="")
        )
        default = input(prompt)
        if default:
            if section not in parser:
                parser.add_section(section)
            parser[section][option] = default

    with open(str(constants.DEFAULT_CONFIG_FILE), "w", encoding="utf8") as f:
        parser.write(f)

    plug.echo(
        "Configuration file written to {}".format(
            constants.DEFAULT_CONFIG_FILE
        )
    )
