"""
    .. important::

        This test class relies on the vanilla configuration of ``repobee``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
import shutil
import pathlib
import types
from unittest.mock import call, patch, ANY

import pytest

import repobee_plug as plug

import _repobee.constants
import _repobee.ext.defaults
from _repobee import plugin
from _repobee import exception

from _repobee.ext import javac, pylint


from repobee_testhelpers._internal import constants

PLUGINS = constants.PLUGINS


@pytest.fixture(autouse=True)
def unregister_plugins():
    """Unregister all plugins for each test."""
    for p in plug.manager.get_plugins():
        plug.manager.unregister(p)


class TestLoadPluginModules:
    """Tests for load_plugin_modules."""

    def test_load_default_plugins(self):
        default_plugin_qualnames = plugin.get_qualified_module_names(
            _repobee.ext.defaults
        )

        modules = plugin.load_plugin_modules(
            default_plugin_qualnames, allow_qualified=True
        )

        module_names = [mod.__name__ for mod in modules]
        assert module_names == default_plugin_qualnames

    def test_load_bundled_plugins(self):
        """Test load the bundled plugins that are not default plugins."""
        bundled_plugin_qualnames = plugin.get_qualified_module_names(
            _repobee.ext
        )
        bundled_plugin_names = plugin.get_module_names(_repobee.ext)

        modules = plugin.load_plugin_modules(bundled_plugin_names)

        module_names = [mod.__name__ for mod in modules]
        assert module_names == bundled_plugin_qualnames

    def test_load_no_plugins(self, no_config_mock):
        """Test calling load plugins when no plugins are specified results in
        no plugins being loaded."""
        modules = plugin.load_plugin_modules([])
        assert not modules

    def test_raises_when_loading_invalid_module(self, empty_config_mock):
        """Test that PluginLoadError is raised when when the plugin specified
        does not exist.
        """
        plugin_name = "this_plugin_does_not_exist"

        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.load_plugin_modules([plugin_name])

        assert "failed to load plugin module " + plugin_name in str(
            exc_info.value
        )

    def test_raises_when_loading_default_plugins_without_allow_qualified(self):
        """Default plugins can only be loaded by their qualified names, and it
        should only be allowed if allow_qualify is True.
        """
        default_plugin_qualnames = plugin.get_qualified_module_names(
            _repobee.ext.defaults
        )

        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.load_plugin_modules(default_plugin_qualnames)

        assert "failed to load plugin module" in str(exc_info.value)


class TestRegisterPlugins:
    """Tests for register_plugins."""

    def test_register_module(self, plugin_manager_mock):
        """Test registering a plugin module with module level hooks."""
        plugin.register_plugins([pylint])
        plugin_manager_mock.register.assert_called_once_with(pylint)

    def test_register_module_with_plugin_class(self, plugin_manager_mock):
        """Test that both the module itself and the class (instance) are
        registered."""
        expected_calls = [call(javac), call(ANY)]

        plugin.register_plugins([javac])

        plugin_manager_mock.register.assert_has_calls(expected_calls)

    def test_register_modules_and_classes(self, plugin_manager_mock):
        """Test that both module level hooks and class hooks are registered
        properly at the same time.

        Among other things, checks the reverse order of registration.
        """
        modules = [javac, pylint]
        # pylint should be registered before javac because of FIFO order
        expected_calls = [call(pylint), call(javac), call(ANY)]
        plugin.register_plugins(modules)

        plugin_manager_mock.register.assert_has_calls(expected_calls)


class TestTryRegisterPlugin:
    """Tests for try_register_plugin."""

    @pytest.fixture(autouse=True)
    def unregister_all_plugins(self):
        plugin.unregister_all_plugins()

    def test_modules_unregistered_after_success(self):
        plugin.try_register_plugin(pylint)
        assert not plug.manager.get_plugins()

    def test_modules_and_classes_unregistered_after_success(self):
        plugin.try_register_plugin(javac, javac.JavacCloneHook)
        assert not plug.manager.get_plugins()

    def test_does_not_unregister_unrelated_plugins(self):
        plug.manager.register(pylint)
        plugin.try_register_plugin(javac, javac.JavacCloneHook)
        assert pylint in plug.manager.get_plugins()

    def test_modules_unregistered_after_fail(self):
        with pytest.raises(plug.PlugError):
            plugin.try_register_plugin(pylint, javac.JavacCloneHook)
        assert not plug.manager.get_plugins()

    def test_fails_if_classes_not_specified(self):
        with pytest.raises(plug.PlugError) as exc_info:
            plugin.try_register_plugin(javac)
        assert javac.JavacCloneHook.__name__ in str(exc_info.value)


class TestInitializePlugins:
    """Tests for the initialize_plugins function."""

    @pytest.mark.skipif(
        len(plug.deprecated_hooks()) == 0,
        reason="There are currently no deprecated hooks",
    )
    def test_deprecation_warning_is_emitted_for_deprecated_hook(
        self, monkeypatch
    ):
        deprecated_hook = "clone_parser_hook"
        assert (
            deprecated_hook in plug.deprecated_hooks()
        ), "hook used here must actually be deprecated"

        # dynamically create a module with a deprecated hook function
        @plug.repobee_hook
        def clone_parser_hook(self, clone_parser):
            pass

        mod_name = "repobee-deprecation-test-plugin"
        mod = types.ModuleType(mod_name)
        mod.__dict__[deprecated_hook] = clone_parser_hook

        monkeypatch.setattr
        with patch(
            "_repobee.plugin.load_plugin_modules",
            autospec=True,
            return_value=[mod],
        ), patch("repobee_plug.log.warning", autospec=True) as warning_mock:
            plugin.initialize_plugins([mod_name])

        assert warning_mock.called

    def test_raises_on_qualified_names_by_default(self):
        qualname = "_repobee.ext.query"
        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.initialize_plugins([qualname])

        assert "Qualified names not allowed" in str(exc_info.value)

    def test_raises_on_filepath_by_default(self, tmpdir):
        plugin_file = pathlib.Path(str(tmpdir)) / "pylint.py"
        shutil.copy(_repobee.ext.javac.__file__, str(plugin_file))

        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.initialize_plugins([str(plugin_file)])

        assert "Filepaths not allowed" in str(exc_info.value)

    def test_initialize_from_filepath_filepath(self, tmpdir):
        """Test initializing a plugin that's specified by a filepath."""
        plugin_file = pathlib.Path(str(tmpdir)) / "pylint.py"
        shutil.copy(_repobee.ext.pylint.__file__, str(plugin_file))

        initialized_plugins = plugin.initialize_plugins(
            [str(plugin_file)], allow_filepath=True
        )

        assert len(initialized_plugins) == 1
        assert initialized_plugins[0].__file__ == str(plugin_file)

    def test_raises_when_filepath_is_not_python_module(self, tmpdir):
        not_a_python_module = pathlib.Path(str(tmpdir)) / "some_file.txt"
        not_a_python_module.write_text(
            "This is definitely\nnot a Python module"
        )

        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.initialize_plugins(
                [str(not_a_python_module)], allow_filepath=True
            )

        assert f"failed to load plugin module {not_a_python_module}" in str(
            exc_info.value
        )


class TestInitializeDistPlugins:
    """Tests for the initialize_dist_plugins function."""

    def test_raises_if_dist_install_is_false(self, monkeypatch):
        """If distinfo.DIST_INSTALL is False, it should not be possible to
        initialize dist plugins.
        """
        monkeypatch.setattr("_repobee.distinfo.DIST_INSTALL", False)

        with pytest.raises(exception.PluginLoadError) as exc_info:
            plugin.initialize_dist_plugins()

        assert "Dist plugins can only be loaded with installed RepoBee" in str(
            exc_info.value
        )
