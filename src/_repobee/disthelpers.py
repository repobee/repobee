"""Helper functions for the distribution."""
import pathlib
import json
import types
import importlib

from typing import Optional, List

import requests
import repobee_plug as plug

import _repobee.ext
from _repobee import distinfo
from _repobee import plugin


def get_installed_plugins_path() -> pathlib.Path:
    """Return the path to the installed_plugins.json file."""
    return distinfo.INSTALL_DIR / "installed_plugins.json"


def get_installed_plugins(
    installed_plugins_path: Optional[pathlib.Path] = None,
) -> dict:
    """Return the public content of the installed_plugins.json file."""
    installed_plugins = _get_installed_plugins(installed_plugins_path)
    if "_metainfo" in installed_plugins:
        del installed_plugins["_metainfo"]
    return installed_plugins


def _get_installed_plugins(
    installed_plugins_path: Optional[pathlib.Path] = None,
):
    """Return the content of the installed_plugins.json file, with metainfo."""
    return json.loads(
        (installed_plugins_path or get_installed_plugins_path()).read_text(
            "utf8"
        )
    )


def write_installed_plugins(
    installed_plugins: dict,
    installed_plugins_path: Optional[pathlib.Path] = None,
) -> None:
    """Write the installed_plugins.json file."""
    path = installed_plugins_path or get_installed_plugins_path()
    metainfo = _get_installed_plugins(path).get("_metainfo") or {}
    metainfo.update(installed_plugins.get("_metainfo") or {})

    installed_plugins_write = dict(installed_plugins)
    installed_plugins_write["_metainfo"] = metainfo
    path.write_text(
        json.dumps(installed_plugins_write, indent=4), encoding="utf8"
    )


def get_active_plugins(
    installed_plugins_path: Optional[pathlib.Path] = None,
) -> List[str]:
    """Read active plugins from the installed_plugins.json file."""
    installed_plugins = _get_installed_plugins(installed_plugins_path)
    return (installed_plugins.get("_metainfo") or {}).get(
        "active_plugins"
    ) or []


def write_active_plugins(
    active_plugins: List[str],
    installed_plugins_path: Optional[pathlib.Path] = None,
) -> None:
    """Write the active plugins."""
    installed_plugins = _get_installed_plugins(installed_plugins_path)
    installed_plugins.setdefault("_metainfo", {})[
        "active_plugins"
    ] = active_plugins
    write_installed_plugins(installed_plugins, installed_plugins_path)


def get_pip_path() -> pathlib.Path:
    """Return the path to the installed pip binary."""
    return distinfo.INSTALL_DIR / "env" / "bin" / "pip"


def get_plugins_json(url: str = "https://repobee.org/plugins.json") -> dict:
    """Fetch and parse the plugins.json file.

    Args:
        url: URL to the plugins.json file.
    Returns:
        A dictionary with the contents of the plugins.json file.
    """
    resp = requests.get(url)
    if resp.status_code != 200:
        plug.log.error(resp.content.decode("utf8"))
        raise plug.PlugError(f"could not fetch plugins.json from '{url}'")
    return resp.json()


def get_builtin_plugins(ext_pkg: types.ModuleType = _repobee.ext) -> dict:
    """Returns a dictionary of builting plugins on the same form as the
    plugins.json dict.
    """

    def _get_plugin_description(name):
        return (
            importlib.import_module(f"{ext_pkg.__name__}.{name}").__dict__.get(
                "PLUGIN_DESCRIPTION"
            )
            or "-"
        )

    return {
        name: dict(
            description=_get_plugin_description(name),
            url="https://repobee.readthedocs.io/en/stable/plugins.html",
            versions={"N/A": {}},
            builtin=True,
        )
        for name in plugin.get_module_names(ext_pkg)
    }
