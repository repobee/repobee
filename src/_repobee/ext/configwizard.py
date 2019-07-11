"""A plugin that adds the ``config-wizard`` command to RepoBee. It runs through
a short configuration wizard that lets the user set RepoBee's defaults.

.. module:: configwizard
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import repobee_plug as plug
import daiquiri

from _repobee import apimeta

LOGGER = daiquiri.getLogger(__file__)


def command(args: argparse.Namespace, api: apimeta.API) -> None:
    LOGGER.info("successfully called config-wizard: {}".format(args))


@plug.repobee_hook
def create_extension_command():
    parser = plug.RepoBeeExtensionParser()
    parser.add_argument("-b", "--bb", help="A useless argument")
    return plug.ExtensionCommand(
        parser=parser,
        name="config-wizard",
        help="Config wizard",
        description="Description of config wizard",
        callback=command,
    )
