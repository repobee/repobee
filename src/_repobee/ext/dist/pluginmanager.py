"""Plugin manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import argparse
import subprocess

import daiquiri
import repobee_plug as plug


import _repobee.distinfo

LOGGER = daiquiri.getLogger(__file__)
PLUGIN = "pluginmanager"


class InstallPluginCommand(plug.Plugin):
    """Extension command for installing a plugin."""

    def _install_plugin(
        self, args: argparse.ArgumentParser, api: None
    ) -> None:
        """Install a plugin."""
        version = (
            args.version
            if args.version.startswith("v")
            else f"v{args.version}"
        )
        plugin_name = (
            args.name
            if args.name.startswith("repobee-")
            else f"repobee-{args.name}"
        )
        plugin_url = (
            f"git+https://github.com/repobee/" f"{plugin_name}.git@{version}"
        )
        cmd = [
            str(_repobee.distinfo.PYTHON_INTERPRETER),
            "-m",
            "pip",
            "install",
            "--upgrade",
            plugin_url,
        ]
        proc = subprocess.run(cmd)

        if proc.returncode != 0:
            LOGGER.exception(f"Failed to install {args.name} {args.version}")
            raise plug.PlugError(
                f"could not install {args.name} {args.version}"
            )

        LOGGER.info(f"Installed {args.name} {args.version}")

    def create_extension_command(self):
        parser = plug.ExtensionParser()
        parser.add_argument(
            "--name", help="Name of the plugin.", type=str, required=True
        )
        parser.add_argument(
            "--version",
            help="The version to install. Should be on the form "
            "'MAJOR.MINOR.PATCH'. Example: '1.2.0'",
            type=str,
            required=True,
        )
        return plug.ExtensionCommand(
            parser=parser,
            name="install-plugin",
            help="Install a plugin.",
            description="Install a plugin.",
            callback=self._install_plugin,
        )
