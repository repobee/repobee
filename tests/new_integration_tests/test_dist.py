"""Tests for the RepoBee installable distribution."""

import pytest
import tempfile
import pathlib
import subprocess
import os

INSTALL_SCRIPT = (
    pathlib.Path(__file__).parent.parent.parent / "scripts" / "install.sh"
)
assert INSTALL_SCRIPT.is_file(), "unable to find install script"


@pytest.fixture(autouse=True)
def install_dir():
    """Install the RepoBee distribution into a temporary directory."""
    with tempfile.TemporaryDirectory() as install_dirname:
        install_dir = pathlib.Path(install_dirname)
        env = dict(os.environ)
        env["REPOBEE_INSTALL_DIR"] = str(install_dir)

        # remove any paths from the path that lead to a virtual environment
        # such that the global Python interpreter is used to create the new
        # venv
        virtualenv_dir = env["VIRTUAL_ENV"]
        paths = [
            path
            for path in env["PATH"].split(":")
            if not path.startswith(virtualenv_dir)
        ]
        env["PATH"] = ":".join(paths)

        subprocess.run("which python".split(), env=env)

        proc = subprocess.Popen(str(INSTALL_SCRIPT), env=env,)
        proc.communicate("n")  # 'n' in answering whether or not to add to PATH
        assert proc.returncode == 0

        yield install_dir


def test_install_dist(install_dir):
    """Test that the distribution is installed correctly."""
    assert (install_dir / "bin" / "repobee").is_file()
    assert (install_dir / "installed_plugins.json").is_file()
    assert (install_dir / "env" / "bin" / "pip").is_file()
