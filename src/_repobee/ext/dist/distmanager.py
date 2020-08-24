"""Distribution manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
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
        plug.echo("Upgrading RepoBee ...")
        repobee_requirement = "repobee" + (
            self.version_spec if self.version_spec else ""
        )

        upgrade = disthelpers.pip(
            "install", repobee_requirement, upgrade=True, no_cache=True
        )
        if upgrade.returncode != 0:
            raise plug.PlugError("failed to upgrade RepoBee")

        plug.echo("RepoBee succesfully upgraded!")
