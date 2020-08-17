"""Distribution manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import subprocess
import sys

import repobee_plug as plug

from _repobee import disthelpers

manage_category = plug.cli.category(
    "manage",
    action_names=["upgrade"],
    help="manage the RepoBee installation",
    description="Manage the RepoBee installation.",
)


class UpgradeCommand(plug.Plugin, plug.cli.Command):
    """Command for upgrading RepoBee."""

    __settings__ = plug.cli.command_settings(
        action=manage_category.upgrade,
        help="upgrade RepoBee to the latest version",
        description="Upgrade RepoBee to the latest version.",
    )

    def command(self) -> None:
        """Upgrade RepoBee to the latest version."""
        cmd = [
            str(disthelpers.get_pip_path()),
            *"install  --upgrade --no-cache repobee".split(),
        ]
        plug.echo("Upgrading RepoBee ...")
        proc = subprocess.run(cmd, capture_output=True)

        if proc.returncode != 0:
            plug.log.error(proc.stderr.decode(sys.getdefaultencoding()))
            raise plug.PlugError("failed to upgrade RepoBee")

        plug.echo("RepoBee succesfully upgraded!")
