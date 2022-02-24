"""Plugin manager for RepoBee when installed with RepoBee's distribution
tooling.

.. danger::

    This plugin should only be used when using an installed version of RepoBee.
"""
import pathlib
import textwrap
import os
import sys
import subprocess

from typing import Tuple, List, Any, Dict

import tabulate
import bullet  # type: ignore

import repobee_plug as plug

from _repobee import disthelpers
from _repobee import __version__

PLUGIN = "pluginmanager"

PLUGIN_SPEC_SEP = "@"

PLUGIN_PREFIX = "repobee-"

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
        description="Install a plugin. Running this command without options "
        "starts an interactive installer, where you can select plugin and "
        "version to install. Plugins can also be installed non-interactively "
        "with the (mutually exclusive) '--plugin-spec' or '--local' options.",
    )

    non_interactive_install_options = plug.cli.mutually_exclusive_group(
        local=plug.cli.option(
            converter=pathlib.Path,
            help="path to a local plugin to install, either a single file or "
            "a plugin package",
        ),
        plugin_spec=plug.cli.option(
            help="a plugin specifier on the form '<NAME>@<VERSION>' (e.g. "
            "'junit4@v1.0.0') to do a non-interactive install of an official "
            "plugin"
        ),
        git_url=plug.cli.option(
            help="url to a Git repository to install a plugin from (e.g. "
            "'https://github.com/repobee/repobee-junit4.git'), optionally "
            "followed by a version specifier '@<VERSION>' (e.g. "
            "'https://github.com/repobee/repobee-junit4.git@v1.0.0')"
        ),
    )

    def command(self) -> None:
        """Install a plugin."""
        plugins = disthelpers.get_plugins_json()
        installed_plugins = disthelpers.get_installed_plugins()
        active_plugins = disthelpers.get_active_plugins()

        try:
            self._install_plugin(plugins, installed_plugins, active_plugins)
        except disthelpers.DependencyResolutionError as exc:
            raise disthelpers.DependencyResolutionError(
                f"Selected plugin is incompatible with RepoBee {__version__}. "
                "Try upgrading RepoBee and then install the plugin again."
            ) from exc

    def _install_plugin(
        self, plugins: dict, installed_plugins: dict, active_plugins: List[str]
    ) -> None:
        if self.local:
            abspath = self.local.absolute()
            if not abspath.exists():
                raise plug.PlugError(f"no such file or directory: '{abspath}'")

            _install_local_plugin(abspath, installed_plugins)
        elif self.git_url:
            _install_plugin_from_git_repo(self.git_url, installed_plugins)
        else:
            plug.echo("Available plugins:")

            if self.plugin_spec:
                # non-interactive install
                name, version = self._split_plugin_spec(
                    self.plugin_spec, plugins
                )
            else:
                # interactive install
                _list_all_plugins(plugins, installed_plugins, active_plugins)
                name, version = _select_plugin(plugins)

            if name in installed_plugins:
                _uninstall_plugin(name, installed_plugins)

            plug.echo(f"Installing {name}{PLUGIN_SPEC_SEP}{version}")
            _install_plugin(name, version, plugins)

            plug.echo(f"Successfully installed {name}@{version}")

            installed_plugins[name] = dict(version=version)
            disthelpers.write_installed_plugins(installed_plugins)

    @staticmethod
    def _split_plugin_spec(plugin_spec: str, plugins: dict) -> Tuple[str, str]:
        parts = plugin_spec.split(PLUGIN_SPEC_SEP)
        if len(parts) != 2:
            raise plug.PlugError(f"malformed plugin spec '{plugin_spec}'")

        name, version = parts

        if name not in plugins:
            raise plug.PlugError(f"no plugin with name '{name}'")
        elif version not in plugins[name]["versions"]:
            raise plug.PlugError(f"plugin '{name}' has no version '{version}'")

        return name, version


def _install_local_plugin(plugin_path: pathlib.Path, installed_plugins: dict):
    install_info: Dict[str, Any] = dict(version="local", path=str(plugin_path))

    if plugin_path.is_dir():
        _check_has_plugin_prefix(plugin_path.name)

        disthelpers.pip(
            "install",
            "-e",
            str(plugin_path),
            f"repobee=={__version__}",
            upgrade=True,
        )
        ident = plugin_path.name[len(PLUGIN_PREFIX) :]
    else:
        ident = str(plugin_path)
        install_info["single_file"] = True

    installed_plugins[ident] = install_info
    disthelpers.write_installed_plugins(installed_plugins)
    plug.echo(f"Installed {ident}")


def _select_plugin(plugins: dict) -> Tuple[str, str]:
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
    install_proc = _install_plugin_from_url_nocheck(install_url)
    if install_proc.returncode != 0:
        raise plug.PlugError(f"could not install {name} {version}")


def _install_plugin_from_git_repo(
    repo_url: str, installed_plugins: dict
) -> None:
    url, *version = repo_url.split(PLUGIN_SPEC_SEP)
    plugin_name = _parse_plugin_name_from_git_url(url)

    install_url = f"git+{repo_url}"
    install_proc = _install_plugin_from_url_nocheck(install_url)
    if install_proc.returncode != 0:
        raise plug.PlugError(f"could not install plugin from {repo_url}")

    install_info = dict(name=url, version=repo_url)
    installed_plugins[plugin_name] = install_info
    disthelpers.write_installed_plugins(installed_plugins)
    plug.echo(f"Installed {plugin_name} from {repo_url}")


def _parse_plugin_name_from_git_url(url: str) -> str:
    stripped_url = url[:-4] if url.endswith(".git") else url
    repo_name = pathlib.Path(stripped_url).name
    _check_has_plugin_prefix(repo_name)
    return pathlib.Path(stripped_url).name[len(PLUGIN_PREFIX) :]


def _check_has_plugin_prefix(s: str) -> None:
    if not s.startswith(PLUGIN_PREFIX):
        raise plug.PlugError(
            "RepoBee plugin package names must be prefixed with "
            f"'{PLUGIN_PREFIX}'"
        )


def _install_plugin_from_url_nocheck(
    install_url: str,
) -> subprocess.CompletedProcess:
    return disthelpers.pip(
        "install",
        install_url,
        f"repobee=={__version__}",  # force RepoBee to stay the same version
        upgrade=True,
    )


class UninstallPluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for uninstall a plugin."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.uninstall,
        help="uninstall a plugin",
        description="Uninstall a plugin. Running this command without options "
        "starts an interactive uninstall wizard. Running with the "
        "'--plugin-name' option non-interactively uninstall the specified "
        "plugin.",
    )

    plugin_name = plug.cli.option(
        help="name of a plugin to uninstall (non-interactive)"
    )

    def command(self) -> None:
        """Uninstall a plugin."""
        installed_plugins = {
            name: attrs
            for name, attrs in disthelpers.get_installed_plugins().items()
            if not attrs.get("builtin")
        }

        if self.plugin_name:
            # non-interactive uninstall
            if self.plugin_name not in installed_plugins:
                raise plug.PlugError(
                    f"no plugin '{self.plugin_name}' installed"
                )
            selected_plugin_name = self.plugin_name
        else:
            # interactive uninstall
            if not installed_plugins:
                plug.echo("No plugins installed")
                return

            plug.echo("Installed plugins:")
            _list_installed_plugins(
                installed_plugins, disthelpers.get_active_plugins()
            )

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
    uninstalled = (
        disthelpers.pip(
            "uninstall", "-y", f"{PLUGIN_PREFIX}{plugin_name}"
        ).returncode
        == 0
    )
    if not uninstalled:
        raise plug.PlugError(f"could not uninstall {plugin_name}")


class ActivatePluginCommand(plug.Plugin, plug.cli.Command):
    """Extension command for activating and deactivating plugins."""

    __settings__ = plug.cli.command_settings(
        action=plugin_category.activate,
        help="activate and deactivate plugins",
        description="Activate and deactivate plugins. Running the command "
        "without options starts an interactive wizard for toggling the "
        "active-status of all installed plugins. Specifying the "
        "'--plugin-name' option non-interactively toggles the active-status "
        "for a single plugin.",
    )

    plugin_name = plug.cli.option(
        help="a plugin to toggle activation status for (non-interactive)"
    )

    def command(self) -> None:
        """Activate a plugin."""
        installed_plugins = disthelpers.get_installed_plugins()
        active = disthelpers.get_active_plugins()

        names = list(installed_plugins.keys()) + list(
            disthelpers.get_builtin_plugins().keys()
        )

        if self.plugin_name:
            # non-interactive activate
            if self.plugin_name not in names:
                raise plug.PlugError(
                    f"no plugin named '{self.plugin_name}' installed"
                )
            selection = (
                active + [self.plugin_name]
                if self.plugin_name not in active
                else list(set(active) - {self.plugin_name})
            )
        else:
            # interactive activate
            default = [i for i, name in enumerate(names) if name in active]
            selection = bullet.Check(
                choices=names,
                prompt="Select plugins to activate (space to check/un-check, "
                "enter to confirm selection):",
            ).launch(default=default)

        disthelpers.write_active_plugins(selection)

        self._echo_state_change(active_before=active, active_after=selection)

    @staticmethod
    def _echo_state_change(
        active_before: List[str], active_after: List[str]
    ) -> None:
        activations = set(active_after) - set(active_before)
        deactivations = set(active_before) - set(active_after)
        if activations:
            plug.echo(f"Activating: {' '.join(activations)}")
        if deactivations:
            plug.echo(f"Deactivating: {' '.join(deactivations)}")


def _wrap_cell(text: str, width: int = 40) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def _list_all_plugins(
    plugins: dict, installed_plugins: dict, active_plugins: List[str]
) -> None:
    headers = [
        "Name",
        "Description",
        "URL",
        "Latest",
        "Installed\n(√ = active)",
    ]
    plugins_table = []
    for plugin_name, attrs in plugins.items():
        latest_version = list(attrs["versions"].keys())[0]
        installed = installed_plugins.get(plugin_name) or {}
        installed_version = (
            "built-in"
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

    pretty_table = _format_table(
        plugins_table,
        headers,
        max_width=_get_terminal_width(),
        column_elim_order=[2, 3, 4, 1, 0],
    )

    plug.echo(pretty_table)


def _list_installed_plugins(
    installed_plugins: dict, active_plugins: List[str]
) -> None:
    headers = ["Name", "Installed version\n(√ = active)"]
    plugins_table = []
    for plugin_name, attrs in installed_plugins.items():
        installed_version = attrs["version"] + (
            " √" if plugin_name in active_plugins else ""
        )
        plugins_table.append([plugin_name, installed_version])

    pretty_table = _format_table(
        plugins_table,
        headers,
        max_width=_get_terminal_width(),
        column_elim_order=[1, 0],
    )
    plug.echo(pretty_table)


def _list_plugin(plugin_name: str, plugins: dict) -> None:
    attrs = plugins[plugin_name]
    table = [
        ["Name", plugin_name],
        ["Description", _wrap_cell(attrs["description"])],
        ["Versions", _wrap_cell(" ".join(attrs["versions"].keys()))],
        ["URL", attrs["url"]],
    ]
    plug.echo(tabulate.tabulate(table, tablefmt="fancy_grid"))


def _format_table(
    table: List[List[str]],
    headers: List[str],
    max_width: int,
    column_elim_order: List[int],
) -> str:
    """Format a table to fit the max width."""
    assert table
    assert headers and column_elim_order
    assert len(headers) == len(column_elim_order)
    assert max_width > 0

    header_elimination_order = [headers[i] for i in column_elim_order]

    # this is extremely inefficient, but as the table is so small it doesn't
    # matter
    mutable_table = list(table)
    mutable_hdrs = list(headers)
    for hdr in header_elimination_order:
        pretty_table = tabulate.tabulate(
            mutable_table, mutable_hdrs, tablefmt="fancy_grid"
        )
        table_width = len(pretty_table.split("\n", maxsplit=1)[0])

        if table_width <= max_width:
            break

        plug.log.warning(
            f"Terminal < {table_width} cols wide, truncating: '{hdr}'"
        )
        elim_idx = mutable_hdrs.index(hdr)
        mutable_hdrs.pop(elim_idx)
        mutable_table = [
            row[:elim_idx] + row[elim_idx + 1 :] for row in mutable_table
        ]

    return pretty_table


def _get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        # if there is no tty, there will be no terminal size
        # so we simply set it to max
        return sys.maxsize
