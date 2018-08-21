"""
    .. important::

        This test class relies on the vanilla configuration of ``repomate``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
import pytest
import os
import builtins
from unittest.mock import call, MagicMock

import repomate
from repomate import plugin
from repomate import hookspec
from repomate import exception

PLUGINS = pytest.constants.PLUGINS


class TestLoadPluginModules:
    """Tests for loda_plugin_modules"""

    def test_load_all_default_plugins(self, config_mock):
        """Test load the default plugins, i.e. the ones listed in
        pytest.constants.PLUGINS.
        """
        expected_names = list(map(plugin.PLUGIN_QUALNAME, PLUGINS))

        modules = plugin.load_plugin_modules(str(config_mock))
        module_names = [mod.__name__ for mod in modules]

        assert module_names == expected_names

    def test_load_no_plugins(self, no_config_mock):
        """Test calling load plugins when no plugins are specified in the
        config.
        """
        modules = plugin.load_plugin_modules()

        assert not modules

    def test_load_single_plugin(self, empty_config_mock):
        plugin_name = "javac"
        plugin_qualname = plugin.PLUGIN_QUALNAME(plugin_name)
        config_contents = os.linesep.join(
            ["[DEFAULTS]", "plugins = {}".format(plugin_name)])
        empty_config_mock.write(config_contents)

        modules = plugin.load_plugin_modules(str(empty_config_mock))
        module_names = [mod.__name__ for mod in modules]

        assert module_names == [plugin_qualname]

    def test_raises_when_loading_invalid_module(self, empty_config_mock):
        """Test that PluginError is raised when when the plugin specified
        does not exist.
        """
        plugin_name = "this_plugin_does_not_exist"
        config_contents = os.linesep.join(
            ["[DEFAULTS]", "plugins = {}".format(plugin_name)])
        empty_config_mock.write(config_contents)

        with pytest.raises(exception.PluginError) as exc:
            plugin.load_plugin_modules(str(empty_config_mock))

        assert "failed to load plugin module " + plugin_name in str(exc)


class TestRegisterPlugins:
    """Tests for register_plugins."""

    @pytest.fixture
    def javac_clone_hook_mock(self, monkeypatch):
        """Return an instance of the clone hook mock"""
        instance_mock = MagicMock()
        class_mock = MagicMock(
            spec='repomate.ext.javac.JavacCloneHook._class',
            return_value=instance_mock)
        monkeypatch.setattr('repomate.ext.javac.JavacCloneHook._class',
                            class_mock)
        return instance_mock

    def test_register_module(self, plugin_manager_mock):
        """Test registering a plugin module with module level hooks."""
        from repomate.ext import pylint

        plugin.register_plugins([pylint])

        plugin_manager_mock.register.assert_called_once_with(pylint)

    def test_register_module_with_plugin_class(self, plugin_manager_mock,
                                               javac_clone_hook_mock):
        """Test that both the module itself and the class (instance) are
        registered."""
        from repomate.ext import javac
        expected_calls = [call(javac), call(javac_clone_hook_mock)]

        plugin.register_plugins([javac])

        plugin_manager_mock.register.assert_has_calls(expected_calls)

    def test_register_modules_and_classes(self, plugin_manager_mock,
                                          javac_clone_hook_mock):
        """Test that both module level hooks and class hooks are registered
        properly at the same time.

        Among other things, checks the reverse order of registration.
        """
        from repomate.ext import javac, pylint
        modules = [javac, pylint]
        # pylint should be registered before javac because of FIFO order
        expected_calls = [
            call(pylint),
            call(javac),
            call(javac_clone_hook_mock),
        ]

        plugin.register_plugins([javac, pylint])

        plugin_manager_mock.register.assert_has_calls(expected_calls)
