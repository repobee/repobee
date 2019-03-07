"""
    .. important::

        This test class relies on the vanilla configuration of ``repomate``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
import os
from unittest.mock import call, MagicMock

import pytest

from repomate import plugin
from repomate import exception

from repomate.plugin import DEFAULT_PLUGIN
from repomate.ext import javac, pylint, defaults

import constants

PLUGINS = constants.PLUGINS


class TestLoadPluginModules:
    """Tests for load_plugin_modules.

    Note that the default plugin repomate.ext.defaults is always loaded.
    """

    def test_load_all_bundled_plugins(self, config_mock):
        """Test load the bundled plugins, i.e. the ones listed in
        constants.PLUGINS.
        """
        expected_names = list(
            map(plugin._plugin_qualname, [*PLUGINS, DEFAULT_PLUGIN])
        )

        modules = plugin.load_plugin_modules(str(config_mock))
        module_names = [mod.__name__ for mod in modules]

        assert module_names == expected_names

    def test_plugin_names_override_config_file(self, config_mock, mocker):
        """Test that the plugin_names argument override the configuration
        file."""
        plugin_names = ["awesome", "the_slarse_plugin", "ric_easter_egg"]
        expected_calls = [
            call(plug)
            for plug in map(
                plugin._plugin_qualname, plugin_names + [DEFAULT_PLUGIN]
            )
        ]

        class module:
            pass

        load_module_mock = mocker.patch(
            "repomate.plugin._try_load_module", return_value=module
        )

        plugin.load_plugin_modules(
            config_file=str(config_mock), plugin_names=plugin_names
        )

        load_module_mock.assert_has_calls(expected_calls)

    def test_load_no_plugins(self, no_config_mock):
        """Test calling load plugins when no plugins are specified results in
        only the default being loaded.
        """
        modules = plugin.load_plugin_modules()

        assert modules == [defaults]

    def test_specify_single_plugin(self, empty_config_mock):
        plugin_name = "javac"
        config_contents = os.linesep.join(
            ["[DEFAULTS]", "plugins = {}".format(plugin_name)]
        )
        empty_config_mock.write(config_contents)

        modules = plugin.load_plugin_modules(str(empty_config_mock))
        module_names = [mod.__name__ for mod in modules]

        assert module_names == list(
            map(plugin._plugin_qualname, [plugin_name, DEFAULT_PLUGIN])
        )

    def test_raises_when_loading_invalid_module(self, empty_config_mock):
        """Test that PluginError is raised when when the plugin specified
        does not exist.
        """
        plugin_name = "this_plugin_does_not_exist"
        config_contents = os.linesep.join(
            ["[DEFAULTS]", "plugins = {}".format(plugin_name)]
        )
        empty_config_mock.write(config_contents)

        with pytest.raises(exception.PluginError) as exc:
            plugin.load_plugin_modules(str(empty_config_mock))

        assert "failed to load plugin module " + plugin_name in str(exc)


class TestRegisterPlugins:
    """Tests for register_plugins."""

    @pytest.fixture
    def javac_clone_hook_mock(self, mocker):
        """Return an instance of the clone hook mock"""
        instance_mock = MagicMock()
        mocker.patch(
            "repomate.ext.javac.JavacCloneHook.__new__",
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
