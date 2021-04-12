"""Tests for the RepoBee installable distribution."""

import tempfile
import collections
import shutil
import json
import os
import pathlib
import shlex
import subprocess
import sys

import pytest
from packaging import version

from unittest import mock
from typing import Optional

import git

import repobee_plug as plug

import repobee
import _repobee

from _repobee import disthelpers, distinfo
from _repobee.ext.dist import pluginmanager


INSTALL_SCRIPT = (
    pathlib.Path(__file__).parent.parent.parent / "scripts" / "install.sh"
)
assert INSTALL_SCRIPT.is_file(), "unable to find install script"


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

    def test_install_local_plugin_file(self, capsys, tmp_path):
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
        hello_py = tmp_path / "hello.py"
        hello_py.write_text(plugin_content, encoding="utf8")

        repobee.run(shlex.split(f"plugin install --local {hello_py}"))

        install_info = disthelpers.get_installed_plugins()[str(hello_py)]
        assert install_info["version"] == "local"
        assert install_info["path"] == str(hello_py)

    def test_install_local_plugin_package(self, tmp_path):
        plugin_version = "1.0.0"

        junit4_local = tmp_path / "repobee-junit4"
        repo = git.Repo.clone_from(
            "https://github.com/repobee/repobee-junit4", to_path=junit4_local
        )
        repo.git.checkout(f"v{plugin_version}")

        repobee.run(shlex.split(f"plugin install --local {junit4_local}"))

        install_info = disthelpers.get_installed_plugins()["junit4"]
        assert install_info["version"] == "local"
        assert install_info["path"] == str(junit4_local)
        assert get_pkg_version("repobee-junit4") == plugin_version

    def test_raises_when_local_package_lacks_repobee_prefix(self, tmp_path):
        junit4_local = tmp_path / "junit4"
        git.Repo.clone_from(
            "https://github.com/repobee/repobee-junit4", to_path=junit4_local
        )

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(shlex.split(f"plugin install --local {junit4_local}"))

        assert "'repobee-'" in str(exc_info.value)

    def test_raises_when_local_points_to_non_existing_path(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            pass

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(shlex.split(f"plugin install --local {tmpfile.name}"))

        assert "no such file or directory" in str(exc_info.value)

    def test_non_interactive_install(self):
        plugin_name = "junit4"
        plugin_version = "v1.0.0"
        cmd = [
            *pluginmanager.plugin_category.install.as_name_tuple(),
            "--plugin-spec",
            f"{plugin_name}{pluginmanager.PLUGIN_SPEC_SEP}{plugin_version}",
        ]

        repobee.run(cmd)

        assert get_pkg_version(
            f"repobee-{plugin_name}"
        ) == plugin_version.lstrip("v")

    def test_raises_on_non_interactive_install_of_non_existing_plugin(self):
        """An error should be raised if one tries to install a plugin that
        does not exist.
        """
        plugin_name = "somepluginthatdoesntexist"
        plugin_version = "v1.0.0"
        cmd = [
            *pluginmanager.plugin_category.install.as_name_tuple(),
            "--plugin-spec",
            f"{plugin_name}{pluginmanager.PLUGIN_SPEC_SEP}{plugin_version}",
        ]

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(cmd)

        assert f"no plugin with name '{plugin_name}'" in str(exc_info.value)

    def test_raises_on_non_interactive_install_of_non_existing_version(self):
        """An error should be raised if one tries to install a version that
        does not exist, but the plugin does.
        """
        plugin_name = "junit4"
        plugin_version = "v0.32.0"
        cmd = [
            *pluginmanager.plugin_category.install.as_name_tuple(),
            "--plugin-spec",
            f"{plugin_name}{pluginmanager.PLUGIN_SPEC_SEP}{plugin_version}",
        ]

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(cmd)

        assert (
            f"plugin '{plugin_name}' has no version '{plugin_version}'"
            in str(exc_info.value)
        )

    def test_raises_on_malformed_plugin_spec(self):
        """An error should be raised if a plugin spec is malformed."""
        malformed_spec = pluginmanager.PLUGIN_SPEC_SEP.join(
            ["too", "many", "parts"]
        )
        cmd = [
            *pluginmanager.plugin_category.install.as_name_tuple(),
            "--plugin-spec",
            malformed_spec,
        ]

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(cmd)

        assert f"malformed plugin spec '{malformed_spec}'" in str(
            exc_info.value
        )

    def test_auto_updates_pip(self):
        """Installing a plugin should automatically update pip if it's
        out-of-date.
        """
        # arrange
        old_pip_version = "20.0.1"
        assert (
            subprocess.run(
                [
                    disthelpers.get_pip_path(),
                    "install",
                    "-U",
                    f"pip=={old_pip_version}",
                ]
            ).returncode
            == 0
        )
        assert version.Version(get_pkg_version("pip")) == version.Version(
            old_pip_version
        )

        plugin_name = "junit4"
        plugin_version = "v1.0.0"
        cmd = [
            *pluginmanager.plugin_category.install.as_name_tuple(),
            "--plugin-spec",
            f"{plugin_name}{pluginmanager.PLUGIN_SPEC_SEP}{plugin_version}",
        ]

        # act
        repobee.run(cmd)

        # assert
        assert version.Version(get_pkg_version("pip")) > version.Version(
            old_pip_version
        )

    def test_install_junit4_plugin_from_remote_git_repository(self):
        url = "https://github.com/repobee/repobee-junit4.git"

        repobee.run(f"plugin install --git-url {url}".split())

        install_info = disthelpers.get_installed_plugins()["junit4"]
        assert install_info["version"] == url
        assert get_pkg_version("repobee-junit4")

    def test_install_specific_version_from_remote_git_repository(self):
        url = "https://github.com/repobee/repobee-junit4.git"
        version = "v1.0.0"

        repobee.run(f"plugin install --git-url {url}@{version}".split())

        install_info = disthelpers.get_installed_plugins()["junit4"]
        assert install_info["version"] == f"{url}@{version}"
        assert get_pkg_version("repobee-junit4") == version.lstrip("v")

    def test_raises_on_incorrectly_named_remote_git_repo(self):
        """If a remote Git repo is not named "repobee-<PLUGIN_NAME>", it should
        not be possible to install.
        """
        url = "https://github.com/slarse/slarse.git"

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(f"plugin install --git-url {url}".split())

        assert (
            "RepoBee plugin package names must be prefixed with 'repobee-'"
        ) in str(exc_info.value)

    def test_raises_on_non_existing_git_url(self):
        url = "https://repobee.org/no/repo/repobee-here.git"

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(f"plugin install --git-url {url}".split())

        assert f"could not install plugin from {url}" in str(exc_info.value)


class TestPluginUninstall:
    """Tests for the ``plugin uninstall`` command."""

    def test_uninstall_installed_plugin(self, mocker):
        plugin_name = "junit4"
        install_plugin(plugin_name, version="v1.0.0")
        mocker.patch("bullet.Bullet.launch", side_effect=[plugin_name])

        repobee.run("plugin uninstall".split())

        assert not get_pkg_version(f"repobee-{plugin_name}")

    def test_non_interactive_uninstall_of_installed_plugin(self):
        plugin_name = "junit4"
        install_plugin(plugin_name, version="v1.0.0")

        cmd = [
            *pluginmanager.plugin_category.uninstall.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]
        repobee.run(cmd)

        assert not get_pkg_version(f"repobee-{plugin_name}")

    def test_raises_on_non_interactive_uninstall_of_non_installed_plugin(self):
        """An error should be raised when trying to uninstall a plugin that
        isn't installed.
        """
        plugin_name = "junit4"
        cmd = [
            *pluginmanager.plugin_category.uninstall.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(cmd)

        assert f"no plugin '{plugin_name}' installed" in str(exc_info.value)


class TestPluginList:
    """Tests for the ``plugin list`` command."""

    def test_truncates_urls_to_fit_terminal_width(self, capsys, mocker):
        """When the terminal is too narrow, the URLs in the plugins table are
        the first to be truncated.
        """
        cols = 120  # URLs need ~140 cols to fit
        mocker.patch(
            "os.get_terminal_size",
            autospec=True,
            return_value=collections.namedtuple("TermSize", "columns lines")(
                columns=cols, lines=100
            ),
        )

        repobee.run("plugin list".split())

        out_err = capsys.readouterr()
        assert "truncating: 'URL'" in out_err.err
        assert "https://github.com" not in out_err.out

    def test_shows_urls_when_terminal_width_is_large(self, capsys, mocker):
        cols = sys.maxsize  # URLs need ~140 cols to fit
        mocker.patch(
            "os.get_terminal_size",
            autospec=True,
            return_value=collections.namedtuple("TermSize", "columns lines")(
                columns=cols, lines=100
            ),
        )

        repobee.run("plugin list".split())

        out_err = capsys.readouterr()
        assert "truncating: 'URL'" not in out_err.err
        assert "https://github.com" in out_err.out


class TestPluginActivate:
    """Tests for the ``plugin activate`` command."""

    def test_non_interactive_activate_of_installed_plugin(self, install_dir):
        plugin_name = "junit4"
        install_plugin(plugin_name, "v1.0.0")

        cmd = [
            *pluginmanager.plugin_category.activate.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]
        repobee.run(cmd)

        assert plugin_name in disthelpers.get_active_plugins(
            install_dir / "installed_plugins.json"
        )

    def test_non_interactive_deactivate_of_builtin_plugin(self, install_dir):
        # arrange
        plugin_name = "ghclassroom"
        cmd = [
            *pluginmanager.plugin_category.activate.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]
        repobee.run(cmd)

        # act
        repobee.run(cmd)

        # assert
        assert plugin_name not in disthelpers.get_active_plugins(
            install_dir / "installed_plugins.json"
        )

    def test_non_interactive_activate_of_builtin_plugin(self, install_dir):
        plugin_name = "ghclassroom"

        cmd = [
            *pluginmanager.plugin_category.activate.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]
        repobee.run(cmd)

        assert plugin_name in disthelpers.get_active_plugins(
            install_dir / "installed_plugins.json"
        )

    def test_raises_on_non_interactive_activate_of_non_installed_plugin(self):
        plugin_name = "junit4"
        cmd = [
            *pluginmanager.plugin_category.activate.as_name_tuple(),
            "--plugin-name",
            plugin_name,
        ]

        with pytest.raises(plug.PlugError) as exc_info:
            repobee.run(cmd)

        assert f"no plugin named '{plugin_name}' installed" in str(
            exc_info.value
        )


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


@pytest.fixture(scope="session")
def install_dir():
    """Install the RepoBee distribution into a temporary directory."""
    with tempfile.TemporaryDirectory() as install_dirname:
        install_dir = pathlib.Path(install_dirname)
        env = dict(os.environ)
        env["REPOBEE_INSTALL_DIR"] = str(install_dir)

        proc = subprocess.Popen(str(INSTALL_SCRIPT), env=env)
        proc.communicate("n")  # 'n' in answering whether or not to add to PATH
        assert proc.returncode == 0

        yield install_dir


@pytest.fixture(scope="session")
def backup_install_dir(install_dir, tmp_path_factory):
    """Backup the install dir such that it can be restored for each test
    function without having to reinstall from scratch.
    """
    backup_root = tmp_path_factory.mktemp("repobee_test_backups")
    repobee_install_backup = backup_root / "repobee_install_backup"
    shutil.copytree(install_dir, repobee_install_backup)
    return repobee_install_backup


@pytest.fixture(autouse=True)
def restore_install_dir(install_dir, backup_install_dir, monkeypatch):
    """Restore the install dir for each test."""
    # moneypatch the distinfo module to make RepoBee think it's installed
    monkeypatch.setattr("_repobee.distinfo.DIST_INSTALL", True)
    monkeypatch.setattr("_repobee.distinfo.INSTALL_DIR", install_dir)
    shutil.rmtree(install_dir)
    shutil.copytree(backup_install_dir, install_dir)


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
