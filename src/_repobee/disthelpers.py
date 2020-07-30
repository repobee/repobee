"""Helper functions for the distribution."""
import pathlib

from _repobee import distinfo


def get_plugin_dir_path() -> pathlib.Path:
    plugin_dir = distinfo.INSTALL_DIR / "installed_plugins"
    plugin_dir.mkdir(exist_ok=True)
    return plugin_dir


def get_interpreter_path() -> pathlib.Path:
    return distinfo.INSTALL_DIR / "env" / "bin" / "python"
