"""Tests for the config category of commands."""
import tempfile

import pytest

from repobee_testhelpers import funcs
from repobee_testhelpers import const

import repobee_plug as plug

import _repobee.exception


class TestConfigShow:
    """Tests for the ``config show`` command."""

    def test_does_not_print_token_by_default(self, capsys):
        """It's very inconvenient for demos if the secure token is printed
        by the show command.
        """
        funcs.run_repobee("config show")

        outerr = capsys.readouterr()
        assert "\ntoken = xxxxxxxxxx\n" in outerr.out
        assert const.TOKEN not in outerr.out
        assert const.TOKEN not in outerr.err

    def test_prints_token_when_asked(self, capsys):
        """It should be possible to show the token on deman."""
        funcs.run_repobee("config show --secrets")

        outerr = capsys.readouterr()
        assert const.TOKEN in outerr.out


class TestConfigVerify:
    """Tests for the ``config verify`` command."""

    def test_raises_if_students_file_does_not_exist(self, platform_url):
        with tempfile.NamedTemporaryFile() as tmpfile:
            pass

        with pytest.raises(_repobee.exception.RepoBeeException) as exc_info:
            funcs.run_repobee(
                f"{plug.cli.CoreCommand.config.verify} "
                f"--base-url {platform_url} "
                f"--students-file {tmpfile.name}"
            )

        assert f"'{tmpfile.name}' is not a file" in str(exc_info.value)
