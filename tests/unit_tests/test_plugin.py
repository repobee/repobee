"""
    .. important::

        This test class relies on the vanilla configuration of ``repobee``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
from unittest.mock import call, MagicMock

import pytest

import _repobee.constants
from _repobee import plugin
from _repobee import exception

from _repobee.ext import javac, pylint

import constants

PLUGINS = constants.PLUGINS


class TestResolvePluginNames:
    """Tests for resolve_plugin_names."""

    def test_plugin_names_override_config_file(self, config_mock, mocker):
        """Test that the plugin_names argument override the configuration
        file."""
        plugin_names = ["awesome", "the_slarse_plugin", "ric_easter_egg"]

        actual_plugin_names = plugin.resolve_plugin_names(
            config_file=str(config_mock), plugin_names=plugin_names
        )

        assert actual_plugin_names == plugin_names


class TestLoadPluginModules:
    """Tests for load_plugin_modules."""

    def test_load_all_bundled_plugins(self):
        """Test load the bundled plugins, i.e. the ones listed in
        constants.PLUGINS.
        """
        plugin_names = [*PLUGINS, _repobee.constants.DEFAULT_PLUGIN]
        plugin_qualnames = list(map(plugin._plugin_qualname, plugin_names))

        modules = plugin.load_plugin_modules(plugin_names)
        module_names = [mod.__name__ for mod in modules]

        assert module_names == plugin_qualnames

    def test_load_no_plugins(self, no_config_mock):
        """Test calling load plugins when no plugins are specified results in
        no plugins being loaded."""
        modules = plugin.load_plugin_modules([])

        assert modules == []

    def test_raises_when_loading_invalid_module(self, empty_config_mock):
        """Test that PluginError is raised when when the plugin specified
        does not exist.
        """
        plugin_name = "this_plugin_does_not_exist"

        with pytest.raises(exception.PluginError) as exc_info:
            plugin.load_plugin_modules([plugin_name])

        assert "failed to load plugin module " + plugin_name in str(
            exc_info.value
        )


class TestRegisterPlugins:
    """Tests for register_plugins."""

    @pytest.fixture
    def javac_clone_hook_mock(self, mocker):
        """Return an instance of the clone hook mock"""
        instance_mock = MagicMock()
        mocker.patch(
            "_repobee.ext.javac.JavacCloneHook.__new__",
            autospec=True,
            return_value=instance_mock,
        )
        return instance_mock

    def test_register_module(self, plugin_manager_mock):
        """Test registering a plugin module with module level hooks."""
        plugin.register_plugins([pylint])

        plugin_manager_mock.register.assert_called_once_with(pylint)

    def test_register_module_with_plugin_class(
        self, plugin_manager_mock, javac_clone_hook_mock
    ):
        """Test that both the module itself and the class (instance) are
        registered."""
        expected_calls = [call(javac), call(javac_clone_hook_mock)]

        plugin.register_plugins([javac])

        plugin_manager_mock.register.assert_has_calls(expected_calls)

    def test_register_modules_and_classes(
        self, plugin_manager_mock, javac_clone_hook_mock
    ):
        """Test that both module level hooks and class hooks are registered
        properly at the same time.

        Among other things, checks the reverse order of registration.
        """
        modules = [javac, pylint]
        # pylint should be registered before javac because of FIFO order
        expected_calls = [
            call(pylint),
            call(javac),
            call(javac_clone_hook_mock),
        ]
        plugin.register_plugins(modules)

        plugin_manager_mock.register.assert_has_calls(expected_calls)
