"""A plugin that adds the ``config-wizard`` command to RepoBee. It runs through
a short configuration wizard that lets the user set RepoBee's defaults.

.. module:: configwizard
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import collections

from typing import Mapping, List, Optional

import bullet  # type: ignore

import repobee_plug as plug

from _repobee import constants


class Wizard(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        category=plug.cli.CoreCommand.config,
        help="Interactive configuration wizard to set up the config file.",
        description=(
            "A configuration wizard that sets up the configuration file. "
            "Warns if there already is a configuration file, as it will be "
            "overwritten."
        ),
    )

    _config: Optional[plug.Config]

    def command(self) -> None:
        assert self._config is not None
        return callback(self.args, self._config)

    def handle_config(self, config: plug.Config) -> None:
        self._config = config


def callback(args: argparse.Namespace, config: plug.Config) -> None:
    """Run through a configuration wizard."""
    if config.path.exists():
        plug.echo("Editing config file at {}".format(str(config.path)))

    if constants.CORE_SECTION_HDR not in config:
        config.create_section(constants.CORE_SECTION_HDR)

    configurable_args = [
        plug.ConfigurableArguments(
            config_section_name=constants.CORE_SECTION_HDR,
            argnames=list(constants.ORDERED_CONFIGURABLE_ARGS),
        )
    ] + plug.manager.hook.get_configurable_args()

    configurable_args_dict: Mapping[str, List[str]] = collections.defaultdict(
        list
    )
    for ca in configurable_args:
        configurable_args_dict[ca.config_section_name] += ca.argnames

    section = bullet.Bullet(
        prompt="Select a section to configure:",
        choices=list(configurable_args_dict.keys()),
    ).launch()

    plug.echo(
        f"""
Configuring section: {section}
Type config values for the options when prompted.
Press ENTER without inputing a value to pick existing default.

Current defaults are shown in brackets [].
"""
    )
    for option in configurable_args_dict[section]:
        prompt = "Enter default for '{}': [{}] ".format(
            option, config.get(section, option, fallback="")
        )
        default = input(prompt)
        if default:
            if section not in config:
                config.create_section(section)
            config[section][option] = default

    config.store()

    plug.echo(f"Configuration file written to {config.path}")
