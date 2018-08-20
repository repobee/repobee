"""
    .. important::

        This test class relies on the vanilla configuration of ``repomate``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
import pytest
import os
from repomate import plugin

PLUGINS = pytest.constants.PLUGINS


class TestLoadPluginModules:
    """Tests for loda_plugin_modules"""

    def test_load_all_default_plugins(self, config_mock):
        """Test load the default plugins, i.e. the ones listed in
        pytest.constants.PLUGINS.
        """
        expected_names = list(map(plugin.PLUGIN_QUALNAME, PLUGINS))

        modules = plugin.load_plugin_modules()
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

        modules = plugin.load_plugin_modules()
        module_names = [mod.__name__ for mod in modules]

        assert module_names == [plugin_qualname]
