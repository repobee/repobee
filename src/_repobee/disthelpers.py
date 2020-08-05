"""Helper functions for the distribution."""
import pathlib

from _repobee import distinfo


def get_plugin_dir_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "plugins"


def get_interpreter_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "env" / "bin" / "python"


def get_plugins_json_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "plugins.json"


def get_installed_plugins_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "installed_plugins.json"


def get_pip_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "env" / "bin" / "pip"
