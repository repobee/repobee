"""Tests for the RepoBee installable distribution."""

import pytest
import tempfile

import json
import os
import pathlib
import shlex
import subprocess
import sys
import repobee
from _repobee import disthelpers

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


def test_install_dist(install_dir):
    """Test that the distribution is installed correctly."""
    assert (install_dir / "bin" / "repobee").is_file()
    assert (install_dir / "installed_plugins.json").is_file()
    assert (install_dir / "env" / "bin" / "pip").is_file()
    assert (install_dir / "completion" / "bash_completion.sh").is_file()


class TestInstallPlugin:
    """Tests for the ``plugin install`` command.

    Unfortunately, we must mock a bit here as the UI is hard to interface with.
    """

    def test_install_junit4_plugin(self, mocker):
        version = "v1.0.0"
        mocker.patch("bullet.Bullet.launch", side_effect=["junit4", version])

        repobee.run("plugin install".split())

        assert get_pkg_version("repobee-junit4") == version.lstrip("v")


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


def get_pkg_version(pkg_name: str) -> str:
    """Get the version of this package from the distribution environment."""
    pip_proc = disthelpers.pip("list", format="json")
    installed_packages = {
        pkg_info["name"]: pkg_info
        for pkg_info in json.loads(
            pip_proc.stdout.decode(sys.getdefaultencoding())
        )
    }
    return installed_packages[pkg_name]["version"]
