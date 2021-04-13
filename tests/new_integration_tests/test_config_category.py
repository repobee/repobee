"""Tests for the config category of commands."""
import tempfile
import pathlib
import shlex

from unittest import mock

import pytest

from repobee_testhelpers import funcs
from repobee_testhelpers import const

import repobee_plug as plug

import _repobee.exception
import _repobee.main


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
        """It should be possible to show the token on demand."""
        funcs.run_repobee("config show --secrets")

        outerr = capsys.readouterr()
        assert const.TOKEN in outerr.out

    def test_prints_local_config(self, capsys, tmp_path):
        """Local (in the working dir) repobee.ini files should take precedence
        over the default config file.
        """
        config_content = "[repobee]\nuser = some-unlikely-user"
        local_config = tmp_path / "repobee.ini"
        local_config.write_text(config_content, encoding="utf8")

        _repobee.main.main(
            ["repobee", *plug.cli.CoreCommand.config.show.as_name_tuple()],
            workdir=tmp_path,
        )

        assert config_content in capsys.readouterr().out

    def test_finds_local_config_in_parent_directory(self, capsys, tmp_path):
        """The config lookup should walk up the directory structure and use the
        first repobee.ini that's encountered.
        """
        # arrange
        config_content = "[repobee]\nuser = some-unlikely-user"
        local_config = tmp_path / "repobee.ini"
        local_config.write_text(config_content, encoding="utf8")

        workdir = tmp_path / "some" / "sub" / "dir"
        workdir.mkdir(parents=True)

        # act
        _repobee.main.main(
            ["repobee", *plug.cli.CoreCommand.config.show.as_name_tuple()],
            workdir=workdir,
        )

        # assert
        assert config_content in capsys.readouterr().out


class TestConfigVerify:
    """Tests for the ``config verify`` command."""

    def test_raises_if_students_file_does_not_exist(self, platform_url):
        with tempfile.NamedTemporaryFile() as tmpfile:
            pass

        non_existing_file = pathlib.Path(tmpfile.name).resolve(strict=False)

        with pytest.raises(_repobee.exception.RepoBeeException) as exc_info:
            funcs.run_repobee(
                f"{plug.cli.CoreCommand.config.verify} "
                f"--base-url {platform_url} "
                f"--students-file {non_existing_file}"
            )

        assert f"'{non_existing_file}' is not a file" in str(exc_info.value)


class TestConfigWizard:
    """Tests for the ``config wizard`` command."""

    def test_respects_config_file_argument(self, platform_url, tmp_path):
        # arrange
        config_file = tmp_path / "repobee.ini"
        unlikely_value = "badabimbadabum"

        # act
        with mock.patch(
            "bullet.Bullet.launch",
            autospec=True,
            return_value=_repobee.constants.CORE_SECTION_HDR,
        ), mock.patch("builtins.input", return_value=unlikely_value):
            _repobee.main.main(
                shlex.split(
                    f"repobee --config-file {config_file} config wizard"
                )
            )

        # assert
        config = plug.Config(config_file)
        assert (
            config.get(_repobee.constants.CORE_SECTION_HDR, "students_file")
            == unlikely_value
        )

    def test_start_message_respects_config_file_argument(
        self, platform_url, tmp_path, capsys
    ):
        # arrange
        config_file = tmp_path / "repobee.ini"

        config_file.write_text("[repobee]\n")

        # act
        with mock.patch(
            "bullet.Bullet.launch",
            autospec=True,
            return_value=_repobee.constants.CORE_SECTION_HDR,
        ), mock.patch("builtins.input", return_value="dontcare"):
            _repobee.main.main(
                shlex.split(
                    f"repobee --config-file {config_file} config wizard"
                )
            )

        # assert
        assert capsys.readouterr().out.startswith(
            f"Editing config file at {config_file}\n"
        )

    def test_end_message_respects_config_file_argument(
        self, platform_url, tmp_path, capsys
    ):
        # arrange
        config_file = tmp_path / "repobee.ini"

        # act
        with mock.patch(
            "bullet.Bullet.launch",
            autospec=True,
            return_value=_repobee.constants.CORE_SECTION_HDR,
        ), mock.patch("builtins.input", return_value="dontcare"):
            _repobee.main.main(
                shlex.split(
                    f"repobee --config-file {config_file} config wizard"
                )
            )

        # assert
        assert capsys.readouterr().out.endswith(
            f"Configuration file written to {config_file}\n"
        )
