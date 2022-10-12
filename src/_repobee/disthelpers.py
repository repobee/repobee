"""Helper functions for the distribution."""
import importlib
import json
import pathlib
import subprocess
import sys
import types
import os

from typing import Optional, List, Any

import requests
import repobee_plug as plug

import _repobee.ext
from _repobee import distinfo
from _repobee import plugin


class DependencyResolutionError(plug.PlugError):
    """Raise when dependency resolution fails during an install."""


def get_installed_plugins_path() -> pathlib.Path:
    """Return the path to the installed_plugins.json file."""
    assert distinfo.INSTALL_DIR
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
    assert distinfo.INSTALL_DIR
    return distinfo.INSTALL_DIR / "env" / "bin" / "pip"


def get_plugins_json(url: str = "https://repobee.org/plugins.json") -> dict:
    """Fetch and parse the plugins.json file.

    Args:
        url: URL to the plugins.json file.
    Returns:
        A dictionary with the contents of the plugins.json file.
    """
    resp = requests.get(url, timeout=10)
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
            url=f"https://repobee.readthedocs.io/"
            f"en/stable/builtins.html#{name}",
            versions={"N/A": {}},
            builtin=True,
        )
        for name in plugin.get_module_names(ext_pkg)
    }


def pip(command: str, *args, **kwargs) -> subprocess.CompletedProcess:
    """Thin wrapper around the ``pip`` executable in the distribution's virtual
    environment.

    Args:
        command: The command to execute (e.g. "install" or "list").
        args: Positional arguments to ``pip``, passed in order. Flags should
            also be passed here (e.g. `--pre`)
        kwargs: Keyword arguments to ``pip``, passed as ``--key value`` to the
            CLI. If the value is ``True``, the argument is passed as a flag,
            i.e. as ``--key``.
    Returns:
        True iff the command exited with a zero exit status.
    Raises:
        DependencyResolutionError: If the 2020-resolver fails to resolve
            dependencies.
    """
    cli_args = list(args)
    cli_kwargs = [_to_cli_kwarg(key, val) for key, val in kwargs.items()]
    env = dict(os.environ)
    run_pip_func = (
        _run_pip_install if command == "install" else _run_pip_without_prompts
    )
    return run_pip_func(command, cli_args, cli_kwargs, env)


def _to_cli_kwarg(key: str, val: Any) -> str:
    return (
        f"--{key.replace('_', '-')}"
        # True is interpreted as a flag
        + (f"={val}" if val is not True else "")
    )


def _run_pip_install(
    command: str, cli_args: List[str], cli_kwargs: List[str], env: dict
) -> subprocess.CompletedProcess:
    """When running ``pip install``, we must take some extra steps to ensure that
    the environment is ammenable to installing RepoBee. E.g. upgrading pip and
    ensuring that RepoBee's install dir is in the environment.
    """
    cli_args = list(cli_args)
    cli_kwargs = list(cli_kwargs)
    env = dict(env)

    if "pip" not in cli_args:
        # always upgrade pip before running an install to ensure that the
        # 2020-resolver is available
        pip_upgrade_rc = _run_pip_without_prompts(
            "install", cli_args=["-U", "pip"], cli_kwargs=[], env=env
        ).returncode
        assert pip_upgrade_rc == 0

    # REPOBEE_INSTALL_DIR must be available when upgrading RepoBee,
    # or the dist plugins aren't activated
    env["REPOBEE_INSTALL_DIR"] = str(distinfo.INSTALL_DIR)

    # due to the hack in setup.py to edit the distinfo, we must build
    # RepoBee from source
    cli_kwargs.append("--no-binary=repobee")

    return _run_pip_without_prompts(command, cli_args, cli_kwargs, env)


def _run_pip_without_prompts(
    command: str, cli_args: List[str], cli_kwargs: List[str], env: dict
) -> subprocess.CompletedProcess:
    if "--no-input" not in cli_args:
        # we don't want any prompting
        cli_args.insert(0, "--no-input")

    cmd = [str(get_pip_path()), command, *cli_args, *cli_kwargs]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    _check_pip_result(proc)
    return proc


def _check_pip_result(pip_proc: subprocess.CompletedProcess) -> None:
    if pip_proc.returncode != 0:
        stderr = pip_proc.stderr.decode(sys.getdefaultencoding())
        plug.log.error(stderr)

        if "ResolutionImpossible" in stderr:
            raise DependencyResolutionError()
