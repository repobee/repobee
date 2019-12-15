"""
    .. important::

        This test class relies on the vanilla configuration of ``repobee``.
        That is to say, only the default plugins are allowed. If you have
        installed any other plugins, tests in here may fail unexpectedly
        without anything actually being wrong.
"""
import pathlib
import tempfile
import types
from unittest.mock import call, MagicMock, patch

import pytest

import repobee_plug as plug

import _repobee.constants
from _repobee import plugin
from _repobee import exception

from _repobee.ext import javac, pylint


import constants

PLUGINS = constants.PLUGINS


@pytest.fixture(autouse=True)
def unregister_plugins():
    """Unregister all plugins for each test."""
    for p in plug.manager.get_plugins():
        plug.manager.unregister(p)


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
        """Test that PluginLoadError is raised when when the plugin specified
        does not exist.
        """
        plugin_name = "this_plugin_does_not_exist"

        with pytest.raises(exception.PluginLoadError) as exc_info:
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


class TestTasks:
    """Tests for testing RepoBee tasks."""

    def test_tasks_run_on_repo_copies_by_default(self):
        """Test that tasks run on copies of the repos by default."""
        repo_name = "task-10"

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = pathlib.Path(tmpdir)
            repo_path = pathlib.Path(tmpdir) / repo_name
            repo_path.mkdir()

            def act(path: pathlib.Path, api: plug.API):
                return plug.HookResult(
                    hook="bogus",
                    status=plug.Status.SUCCESS,
                    msg="Yay",
                    data={"path": path},
                )

            task = plug.Task(act=act)

            results = plugin._execute_tasks(
                [repo_name], [task], api=None, cwd=cwd
            )

        assert len(results[repo_name]) == 1
        res = results[repo_name][0]
        assert res.data["path"] != repo_path


class TestInitializePlugins:
    """Tests for the initialize_plugins function."""

    def test_deprecation_warning_is_emitted_for_deprecated_hook(
        self, monkeypatch
    ):
        deprecated_hook = "act_on_cloned_repo"
        assert (
            deprecated_hook in plug.deprecated_hooks()
        ), "hook used here must actually be deprecated"

        # dynamically create a module with a deprecated hook function
        @plug.repobee_hook
        def act_on_cloned_repo(self, path, api):
            pass

        mod_name = "repobee-deprecation-test-plugin"
        mod = types.ModuleType(mod_name)
        mod.__dict__[deprecated_hook] = act_on_cloned_repo

        monkeypatch.setattr
        with patch(
            "_repobee.plugin.load_plugin_modules",
            autospec=True,
            return_value=[mod],
        ), patch(
            "_repobee.plugin.LOGGER.warning", autospec=True
        ) as warning_mock:
            plugin.initialize_plugins([mod_name])

        assert warning_mock.called
