"""Tests for the RepoBee installable distribution."""

import pytest
import tempfile

import json
import os
import pathlib
import shlex
import subprocess
import sys

from packaging import version

from unittest import mock
from typing import Optional

import git

import repobee_plug as plug

import repobee
import _repobee

from _repobee import disthelpers, distinfo


INSTALL_SCRIPT = (
    pathlib.Path(__file__).parent.parent.parent / "scripts" / "install.sh"
)
assert INSTALL_SCRIPT.is_file(), "unable to find install script"


@pytest.fixture(autouse=True)
def install_dir(monkeypatch):
    """Install the RepoBee distribution into a temporary directory."""
    with tempfile.TemporaryDirectory() as install_dirname:
        install_dir = pathlib.Path(install_dirname)
        env = dict(os.environ)
        env["REPOBEE_INSTALL_DIR"] = str(install_dir)

        proc = subprocess.Popen(str(INSTALL_SCRIPT), env=env)
        proc.communicate("n")  # 'n' in answering whether or not to add to PATH
        assert proc.returncode == 0

        # moneypatch the distinfo module to make RepoBee think it's installed
        monkeypatch.setattr("_repobee.distinfo.DIST_INSTALL", True)
        monkeypatch.setattr("_repobee.distinfo.INSTALL_DIR", install_dir)

        yield install_dir


@pytest.fixture(autouse=True)
def set_version_in_pluginmanager(monkeypatch):
    """Set the version attribute of the pluginmanager to the same version as
    the installed RepoBee.

    This only matters when there is a mismatch between the latest released
    version, and the version of the current repository.
    """
    monkeypatch.setattr(
        "_repobee.ext.dist.pluginmanager.__version__",
        f"v{get_pkg_version('repobee')}",
    )


def test_install_dist(install_dir):
    """Test that the distribution is installed correctly."""
    assert (install_dir / "bin" / "repobee").is_file()
    assert (install_dir / "installed_plugins.json").is_file()
    assert (install_dir / "env" / "bin" / "pip").is_file()
    assert (install_dir / "completion" / "bash_completion.sh").is_file()


class TestPluginInstall:
    """Tests for the ``plugin install`` command.

    Unfortunately, we must mock a bit here as the UI is hard to interface with.
    """

    def test_install_junit4_plugin(self, mocker):
        version = "v1.0.0"
        mocker.patch("bullet.Bullet.launch", side_effect=["junit4", version])

        repobee.run("plugin install".split())

        assert get_pkg_version("repobee-junit4") == version.lstrip("v")

    def test_cannot_downgrade_repobee_version(self, mocker):
        """Test that installing a version of a plugin that requires an older
        version of RepoBee does fails. In other words, the plugin should not be
        installed and RepoBee should not be downgraded.
        """
        current_version = str(version.Version(_repobee.__version__))
        if get_pkg_version("repobee") != current_version:
            pytest.skip("unreleased version, can't run downgrade test")

        # this version of sanitizer requires repobee==3.0.0-alpha.5
        sanitizer_version = "2110de7952a75c03f4d33e8f2ada78e8aca29c57"
        mocker.patch(
            "bullet.Bullet.launch",
            side_effect=["sanitizer", sanitizer_version],
        )
        repobee_initial_version = get_pkg_version("repobee")

        with pytest.raises(disthelpers.DependencyResolutionError):
            repobee.run("plugin install".split())

        assert get_pkg_version("repobee") == repobee_initial_version

    def test_install_plugin_file_by_path(self, capsys):
        plugin_content = """
import repobee_plug as plug
class Hello(plug.Plugin, plug.cli.Command):
    def command(self):
        return plug.Result(
            name='hello',
            status=plug.Status.SUCCESS,
            msg='Best message'
        )
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            hello_py = workdir / "hello.py"
            hello_py.write_text(plugin_content, encoding="utf8")

            repobee.run(shlex.split(f"plugin install --local {hello_py}"))

            install_info = disthelpers.get_installed_plugins()[str(hello_py)]
            assert install_info["version"] == "local"
            assert install_info["path"] == str(hello_py)

    def test_install_plugin_package_by_path(self):
        plugin_version = "1.0.0"

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            junit4_local = workdir / "repobee-junit4"
            repo = git.Repo.clone_from(
                "https://github.com/repobee/repobee-junit4",
                to_path=junit4_local,
            )
            repo.git.checkout(f"v{plugin_version}")

            repobee.run(shlex.split(f"plugin install --local {junit4_local}"))

            install_info = disthelpers.get_installed_plugins()["junit4"]
            assert install_info["version"] == "local"
            assert install_info["path"] == str(junit4_local)
            assert get_pkg_version("repobee-junit4") == plugin_version

    def test_install_plugin_package_by_path_without_repobee_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            junit4_local = workdir / "junit4"
            git.Repo.clone_from(
                "https://github.com/repobee/repobee-junit4",
                to_path=junit4_local,
            )

            with pytest.raises(plug.PlugError) as exc_info:
                repobee.run(
                    shlex.split(f"plugin install --local {junit4_local}")
                )

            assert "'repobee-'" in str(exc_info.value)


class TestPluginUninstall:
    """Tests for the ``plugin uninstall`` command."""

    def test_uninstall_installed_plugin(self, mocker):
        plugin_name = "junit4"
        install_plugin(plugin_name, version="v1.0.0")
        mocker.patch("bullet.Bullet.launch", side_effect=[plugin_name])

        repobee.run("plugin uninstall".split())

        assert not get_pkg_version(f"repobee-{plugin_name}")


class TestManageUpgrade:
    """Tests for the ``manage upgrade`` command."""

    def test_specific_version(self):
        """Test "upgrading" to a specific version. In this case, it's really
        downgrading, but we don't have a separate command for that.
        """
        version = "2.4.0"
        repobee.run(
            shlex.split(f"manage upgrade --version-spec '=={version}'")
        )

        assert get_pkg_version("repobee") == version

    def test_activates_dist_plugins(self):
        """Test that dist plugins (e.g. the ``plugin`` category of commands)
        are activated properly upon an upgrade.
        """
        repobee.run(
            shlex.split("manage upgrade --version-spec '==v3.0.0-beta.1'")
        )
        proc = run_dist("plugin list")

        assert proc.returncode == 0


def install_plugin(name: str, version: str) -> None:
    # arrange
    with mock.patch("bullet.Bullet.launch", side_effect=[name, version]):
        repobee.run("plugin install".split())
    assert get_pkg_version(f"repobee-{name}")


def get_pkg_version(pkg_name: str) -> Optional[str]:
    """Get the version of this package from the distribution environment."""
    pip_proc = disthelpers.pip("list", format="json")
    installed_packages = {
        pkg_info["name"]: pkg_info
        for pkg_info in json.loads(
            pip_proc.stdout.decode(sys.getdefaultencoding())
        )
    }
    return (
        installed_packages[pkg_name]["version"]
        if pkg_name in installed_packages
        else None
    )


def run_dist(cmd: str) -> subprocess.CompletedProcess:
    """Execute a command with the installed RepoBee executable."""
    repobee_executable = distinfo.INSTALL_DIR / "bin" / "repobee"
    return subprocess.run(shlex.split(f"{repobee_executable} {cmd}"))
