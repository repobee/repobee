"""Distribution manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import json
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
        description="Upgrade RepoBee to the latest version. You can also "
        "specify a specific version to install with the `--version-spec` "
        "option.",
    )

    version_spec = plug.cli.option(
        help="specify a version to install, as described here: "
        "https://pip.pypa.io/en/stable/reference/pip_install/"
        "#requirement-specifiers",
        converter=str,
    )

    def command(self) -> None:
        """Upgrade RepoBee to the latest version."""
        plug.echo(f"Upgrading RepoBee from v{_installed_version()}...")
        repobee_requirement = f"repobee{self.version_spec or ''}"

        upgrade = disthelpers.pip(
            "install",
            repobee_requirement,
            upgrade=True,
            no_cache=True,
            force_reinstall=True,
        )
        if upgrade.returncode != 0:
            raise plug.PlugError("failed to upgrade RepoBee")

        plug.echo(f"RepoBee succesfully upgraded to v{_installed_version()}!")


def _installed_version(package: str = "repobee") -> str:
    return next(
        entry
        for entry in json.loads(
            disthelpers.pip("list", format="json").stdout.decode(
                sys.getdefaultencoding()
            )
        )
        if entry["name"] == package
    )["version"]
