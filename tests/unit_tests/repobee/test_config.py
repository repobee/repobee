import os
from unittest import mock

import pytest

import repobee_plug as plug

from _repobee import config
from _repobee import exception

from repobee_testhelpers._internal import constants

STUDENTS = constants.STUDENTS
USER = constants.USER
BASE_URL = constants.BASE_URL
ORG_NAME = constants.ORG_NAME
TEMPLATE_ORG_NAME = constants.TEMPLATE_ORG_NAME
PLUGINS = constants.PLUGINS
CONFIG_TOKEN = constants.CONFIG_TOKEN


class TestExecuteConfigHooks:
    """Tests for execute_config_hooks."""

    def test_with_no_config_file(self, unused_path, plugin_manager_mock):
        config.execute_config_hooks(config=plug.Config(unused_path))
        assert not plugin_manager_mock.hook.config_hook.called

    def test_with_config_file(self, full_config, plugin_manager_mock):
        config.execute_config_hooks(full_config)

        # TODO assert with a real value instead of mock.ANY
        plugin_manager_mock.hook.config_hook.assert_called_once_with(
            config_parser=mock.ANY
        )


class TestCheckConfigIntegrity:
    """Tests for check_config_integroty."""

    def test_with_well_formed_config(self, config_mock):
        """This should just not raise."""
        config.check_config_integrity(str(config_mock))

    def test_with_well_formed_plugin_options(self, config_mock):
        """Should not raise."""
        config_mock.write(
            os.linesep
            + os.linesep.join(["[some_config]", "option = value", "bla = blu"])
        )

    def test_with_no_config_file_raises(self, unused_path):
        with pytest.raises(exception.FileError) as exc_info:
            config.check_config_integrity(config_file=unused_path)

        assert str(unused_path) in str(exc_info.value)

    def test_with_invalid_defaults_key_raises(self, empty_config_mock):
        empty_config_mock.write(
            os.linesep.join(
                [
                    f"[{plug.Config.CORE_SECTION_NAME}]",
                    "user = someone",
                    "option = value",
                ]
            )
        )
        with pytest.raises(exception.FileError) as exc_info:
            config.check_config_integrity(str(empty_config_mock))

        assert (
            f"config file at {empty_config_mock} contains invalid default keys"
        ) in str(exc_info.value)
        assert "option" in str(exc_info.value)
        assert "user" not in str(exc_info.value)

    def test_with_valid_but_malformed_default_args_raises(
        self, empty_config_mock
    ):
        empty_config_mock.write(
            os.linesep.join(
                [
                    f"[{plug.Config.CORE_SECTION_NAME}]",
                    "user = someone",
                    "base_url",
                    "org_name = cool",
                    "plugins  ",
                ]
            )
        )
        with pytest.raises(exception.FileError) as exc_info:
            config.check_config_integrity(str(empty_config_mock))

        assert "user" not in str(exc_info.value)
        assert "org_name" not in str(exc_info.value)
        assert "base_url" in str(exc_info.value)
        assert "plugins" in str(exc_info.value)
