"""Helper functions for the distribution."""
import pathlib
import json

from typing import Optional, List

import requests
import repobee_plug as plug

from _repobee import distinfo


def get_installed_plugins_path() -> pathlib.Path:
    """Return the path to the installed_plugins.json file."""
    return distinfo.INSTALL_DIR / "installed_plugins.json"


def read_active_plugins(
    installed_plugins_path: Optional[pathlib.Path] = None,
) -> List[str]:
    """Read active plugins from the installed_plugins.json file."""
    installed_plugins = json.loads(
        (installed_plugins_path or get_installed_plugins_path()).read_text(
            "utf8"
        )
    )
    return [
        name
        for name, attrs in installed_plugins.items()
        if attrs.get("active")
    ]


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
