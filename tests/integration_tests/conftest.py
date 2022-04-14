"""Global fixtures for the integration tests."""

import pathlib
import tempfile
import pytest

from repobee_testhelpers import funcs


@pytest.fixture(autouse=True)
def run_repobee_in_tmpdir(monkeypatch):
    """This fixture changes the run_repobee function to automatically run
    in a temporary directory if the workdir keyword argument is not
    provided.
    """
    orig_run_repobee = funcs.run_repobee

    def run_repobee(*args, **kwargs):
        if "workdir" in kwargs:
            return orig_run_repobee(*args, **kwargs)

        # no workdir was specified, so we make a temporary one
        with tempfile.TemporaryDirectory() as tmpdir:
            return orig_run_repobee(
                *args, **kwargs, workdir=pathlib.Path(tmpdir)
            )

    monkeypatch.setattr("repobee_testhelpers.funcs.run_repobee", run_repobee)
