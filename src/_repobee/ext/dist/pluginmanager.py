"""Plugin manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import pathlib
import subprocess
import sys
import textwrap

import typing as ty

import tabulate
import bullet

import repobee_plug as plug

from _repobee import disthelpers
from _repobee import __version

PLUGIN = "pluginmanager"

plugin_category = plug.cli.category(
    name="plugin",
    action_names=["install", "uninstall", "list", "activate"],
    help="manage plugins",
    description="Manage plugins.",
)


class ListPluginsCommand(plug.Plugin, plug.cli.Command):
    """Extension command for listing available plugins."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.list,
        help="list available plugins",
        description="List available plugins. Available plugins are fetched "
        "from https://repobee.org.",
    )

    plugin_name = plug.cli.option(help="A plugin to list detailed info for.")

    def command(self) -> None:
        """List available plugins."""
        plugins = disthelpers.get_plugins_json()
        plugins.update(disthelpers.get_builtin_plugins())
        installed_plugins = disthelpers.get_installed_plugins()
        active_plugins = disthelpers.get_active_plugins()

        if not self.plugin_name:
            _list_all_plugins(plugins, installed_plugins, active_plugins)
        else:
            _list_plugin(self.plugin_name, plugins)


class InstallPluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for installing a plugin."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.install,
        help="install a plugin",
        description="Install a plugin.",
    )

    single_file = plug.cli.option(
        converter=pathlib.Path, help="path to a single-file plugin to activate"
    )

    def command(self) -> None:
        """Install a plugin."""
        plugins = disthelpers.get_plugins_json()
        installed_plugins = disthelpers.get_installed_plugins()
        active_plugins = disthelpers.get_active_plugins()

        if self.single_file:
            abspath = self.single_file.resolve(strict=True)
            installed_plugins[str(abspath)] = dict(
                version="local", single_file=True,
            )
            disthelpers.write_installed_plugins(installed_plugins)
            plug.echo(f"Installed {abspath}")
        else:
            plug.echo("Available plugins:")
            _list_all_plugins(plugins, installed_plugins, active_plugins)
            name, version = _select_plugin(plugins)

            if name in installed_plugins:
                _uninstall_plugin(name, installed_plugins)

            plug.echo(f"Installing {name}@{version}")
            _install_plugin(name, version, plugins)

            plug.echo(f"Successfully installed {name}@{version}")

            installed_plugins[name] = dict(version=version)
            disthelpers.write_installed_plugins(installed_plugins)


def _select_plugin(plugins: dict) -> ty.Tuple[str, str]:
    """Interactively select a plugin."""
    selected_plugin_name = bullet.Bullet(
        prompt="Select a plugin to install:", choices=list(plugins.keys())
    ).launch()

    selected_plugin_attrs = plugins[selected_plugin_name]

    _list_plugin(selected_plugin_name, plugins)

    selected_version = bullet.Bullet(
        prompt="Select a version to install:",
        choices=list(selected_plugin_attrs["versions"].keys()),
    ).launch()

    return selected_plugin_name, selected_version


def _install_plugin(name: str, version: str, plugins: dict) -> None:
    install_url = f"git+{plugins[name]['url']}@{version}"

    cmd = [
        str(disthelpers.get_pip_path()),
        "install",
        "--upgrade",
        install_url,
    ]
    proc = subprocess.run(cmd, capture_output=True)

    if proc.returncode != 0:
        plug.log.error(proc.stderr.decode(sys.getdefaultencoding()))
        raise plug.PlugError(f"could not install {name} {version}")


class UninstallPluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for uninstall a plugin."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.uninstall,
        help="uninstall a plugin",
        description="Uninstall a plugin.",
    )

    def command(self) -> None:
        """Uninstall a plugin."""
        installed_plugins = {
            name: attrs
            for name, attrs in disthelpers.get_installed_plugins().items()
            if not attrs.get("builtin")
        }

        if not installed_plugins:
            plug.echo("No plugins installed")
            return

        plug.echo("Installed plugins:")
        _list_installed_plugins(installed_plugins)

        selected_plugin_name = bullet.Bullet(
            prompt="Select a plugin to uninstall:",
            choices=list(installed_plugins.keys()),
        ).launch()
        _uninstall_plugin(selected_plugin_name, installed_plugins)


def _uninstall_plugin(plugin_name: str, installed_plugins: dict):
    plugin_version = installed_plugins[plugin_name]["version"]
    plug.echo(f"Uninstalling {plugin_name}@{plugin_version}")
    if not installed_plugins[plugin_name].get("single_file"):
        _pip_uninstall_plugin(plugin_name)

    del installed_plugins[plugin_name]
    disthelpers.write_installed_plugins(installed_plugins)
    disthelpers.write_active_plugins(
        [
            name
            for name in disthelpers.get_active_plugins()
            if name != plugin_name
        ]
    )
    plug.echo(f"Successfully uninstalled {plugin_name}")


def _pip_uninstall_plugin(plugin_name: str) -> None:
    cmd = [
        str(disthelpers.get_pip_path()),
        "uninstall",
        "-y",
        f"repobee-{plugin_name}",
    ]
    proc = subprocess.run(cmd, capture_output=True)

    if proc.returncode != 0:
        plug.log.error(proc.stderr.decode(sys.getdefaultencoding()))
        raise plug.PlugError(f"could not uninstall {plugin_name}")


class ActivatePluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for activating and deactivating plugins."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.activate,
        help="activate a plugin",
        description="Activate a plugin.",
    )

    def command(self) -> None:
        """Activate a plugin."""
        installed_plugins = disthelpers.get_installed_plugins()
        active = disthelpers.get_active_plugins()

        names = list(installed_plugins.keys()) + list(
            disthelpers.get_builtin_plugins().keys()
        )

        default = [i for i, name in enumerate(names) if name in active]
        selection = bullet.Check(
            choices=names,
            prompt="Select plugins to activate (space to check/un-check, "
            "enter to confirm selection):",
        ).launch(default=default)

        disthelpers.write_active_plugins(selection)


def _wrap_cell(text: str, width: int = 40) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def _list_all_plugins(
    plugins: dict, installed_plugins: dict, active_plugins: ty.List[str]
) -> None:
    headers = [
        "Name",
        "Description",
        "URL",
        "Latest",
        "Installed (√ = active)",
    ]
    plugins_table = []
    for plugin_name, attrs in plugins.items():
        latest_version = list(attrs["versions"].keys())[0]
        installed = installed_plugins.get(plugin_name) or {}
        installed_version = (
            __version.__version__
            if attrs.get("builtin")
            else (installed.get("version") or "-")
        ) + (" √" if plugin_name in active_plugins else "")
        plugins_table.append(
            [
                plugin_name,
                _wrap_cell(attrs["description"]),
                attrs["url"],
                latest_version,
                installed_version,
            ]
        )

    plug.echo(tabulate.tabulate(plugins_table, headers, tablefmt="fancy_grid"))


def _list_installed_plugins(installed_plugins: dict) -> None:
    headers = ["Name", "Installed version", "Active"]
    plugins_table = []
    for plugin_name, attrs in installed_plugins.items():
        plugins_table.append(
            [plugin_name, attrs["version"], attrs.get("active")]
        )

    plug.echo(
        tabulate.tabulate(
            plugins_table, headers=headers, tablefmt="fancy_grid"
        )
    )


def _list_plugin(plugin_name: str, plugins: dict) -> None:
    attrs = plugins[plugin_name]
    table = [
        ["Name", plugin_name],
        ["Description", _wrap_cell(attrs["description"])],
        ["Versions", _wrap_cell(" ".join(attrs["versions"].keys()))],
        ["URL", attrs["url"]],
    ]
    plug.echo(tabulate.tabulate(table, tablefmt="fancy_grid"))
