"""Helper functions for the distribution."""
import pathlib
import logging

import requests
import repobee_plug as plug

from _repobee import distinfo


def get_installed_plugins_path() -> pathlib.Path:
    """Return the path to the installed_plugins.json file."""
    return distinfo.INSTALL_DIR / "installed_plugins.json"


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
        plug.log(resp.content.decode("utf8"), level=logging.ERROR)
        raise plug.PlugError(f"could not fetch plugins.json from '{url}'")
    return resp.json()
