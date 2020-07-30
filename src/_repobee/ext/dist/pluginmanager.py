"""Plugin manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import subprocess

import daiquiri
import repobee_plug as plug

from _repobee import disthelpers

LOGGER = daiquiri.getLogger(__file__)
PLUGIN = "pluginmanager"

plugin_category = plug.cli.category(
    name="plugin",
    action_names=["install", "uninstall"],
    help="Manage plugins.",
    description="Manage plugins.",
)


class InstallPluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for installing a plugin."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.install,
        help="Install a plugin.",
        description="Install a plugin.",
    )

    version = plug.cli.option(
        help="The version to install. Should be on the form "
        "'MAJOR.MINOR.PATCH. Example: '1.2.0'''",
        converter=str,
        required=True,
    )
    name = plug.cli.option(
        "--name", help="Name of the plugin.", converter=str, required=True
    )

    def command(self, api: None) -> None:
        """Install a plugin."""
        version = (
            self.version
            if self.version.startswith("v")
            else f"v{self.version}"
        )
        plugin_name = (
            self.name
            if self.name.startswith("repobee-")
            else f"repobee-{self.name}"
        )
        plugin_url = (
            f"git+https://github.com/repobee/" f"{plugin_name}.git@{version}"
        )
        cmd = [
            str(disthelpers.get_interpreter_path()),
            "-m",
            "pip",
            "install",
            "--upgrade",
            plugin_url,
        ]
        proc = subprocess.run(cmd)

        if proc.returncode != 0:
            LOGGER.exception(f"Failed to install {self.name} {self.version}")
            raise plug.PlugError(
                f"could not install {self.name} {self.version}"
            )

        LOGGER.info(f"Installed {self.name} {self.version}")


class UninstallPluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for uninstall a plugin."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.uninstall,
        help="Uninstall a plugin.",
        description="Uninstall a plugin.",
    )

    def command(self, api: None) -> None:
        """Uninstall a plugin."""
