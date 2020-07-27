"""Plugin manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import subprocess

import daiquiri
import repobee_plug as plug


import _repobee.distinfo

LOGGER = daiquiri.getLogger(__file__)
PLUGIN = "pluginmanager"

plugin_category = plug.cli.category(name="plugin", action_names=["install"])


class InstallPluginCommand(plug.Plugin):
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
            str(_repobee.distinfo.PYTHON_INTERPRETER),
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
