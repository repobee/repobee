"""Plugin system module.

Module containing plugin system utility functions and classes.

.. module:: plugin
    :synopsis: PLugin system utility functions and classes.

.. moduleauthor:: Simon Larsén
"""
import collections
import contextlib
import shutil
import tempfile

import types
import pathlib
import importlib
from types import ModuleType
from typing import List, Optional, Iterable, Mapping

import daiquiri

import _repobee
from _repobee import config
from _repobee import exception
from _repobee import constants

import repobee_plug as plug

LOGGER = daiquiri.getLogger(__file__)


def _plugin_qualname(plugin_name):
    return "{}.ext.{}".format(_repobee._internal_package_name, plugin_name)


def _external_plugin_qualname(plugin_name):
    return "{}_{plugin_name}.{plugin_name}".format(
        _repobee._external_package_name, plugin_name=plugin_name
    )


def load_plugin_modules(plugin_names: Iterable[str]) -> List[ModuleType]:
    """Load the given plugins. Plugins are loaded such that they are executed
    in the same order that they are specified in the plugin_names list.

    When loading a plugin, tries to import first from :py:mod:`_repobee.ext`,
    and then from ``repobee_<plugin>``. For example, if ``javac`` is listed as
    a plugin, the following imports will be attempted:

    .. code-block:: python

        # import nr 1
        from _repobee.ext import javac

        # import nr 2
        from repobee_javac import javac

    Args:
        plugin_names: A list of plugin names. Overrides the config file.

    Returns:
        a list of loaded modules.
    """
    loaded_modules = []
    LOGGER.debug("Loading plugins: " + ", ".join(plugin_names))

    for name in plugin_names:
        plug_mod = _try_load_module(
            _plugin_qualname(name)
        ) or _try_load_module(_external_plugin_qualname(name))
        if not plug_mod:
            msg = "failed to load plugin module " + name
            raise exception.PluginLoadError(msg)
        loaded_modules.append(plug_mod)
    return loaded_modules


def _try_load_module(qualname: str) -> Optional[ModuleType]:
    """Try to load a module.

    Args:
        qualname: Qualified name of the module.

    Returns:
        the module if loaded properly, None otherwise
    """
    try:
        return importlib.import_module(qualname)
    except ImportError:
        # ImportError in 3.5, ModuleNotFoundError in 3.6+
        # using ImportError for compatability
        return None


def register_plugins(modules: List[ModuleType]) -> None:
    """Register the namespaces of the provided modules, and any plug.Plugin
    instances in them. Registers modules in reverse order as they are
    run in LIFO order.

    Args:
        modules: A list of modules.
    """
    assert all([isinstance(mod, ModuleType) for mod in modules])
    for module in reversed(modules):  # reverse because plugins are run LIFO
        plug.manager.register(module)
        for value in module.__dict__.values():
            if (
                isinstance(value, type)
                and issubclass(value, plug.Plugin)
                and value != plug.Plugin
            ):
                plug.manager.register(value())


def initialize_plugins(plugin_names: List[str] = None):
    """Load and register plugins.

    Args:
        plugin_names: An optional list of plugin names that overrides the
        configuration file's plugins.
    """
    registered_plugins = plug.manager.get_plugins()
    plug_modules = [
        p
        for p in load_plugin_modules(plugin_names=plugin_names)
        if p not in registered_plugins
    ]
    register_plugins(plug_modules)
    _handle_deprecation()


def resolve_plugin_names(
    plugin_names: Optional[List[str]] = None,
    config_file: pathlib.Path = constants.DEFAULT_CONFIG_FILE,
) -> List[str]:
    """Return a list of plugin names to load into RepoBee given a list of
    externally specified plugin names, and a path to a configuration file.

    Args:
        plugin_names: A list of names of plugins.
        config_file: A configuration file.
    Returns:
        A list of plugin names that should be loaded.
    """
    return [*(plugin_names or config.get_plugin_names(config_file) or [])]


def resolve_plugin_version(plugin_module: types.ModuleType,) -> Optional[str]:
    """Return the version of the top-level package containing the plugin, or
    None if it is not defined.
    """
    pkg_name = plugin_module.__package__.split(".")[0]
    pkg_module = _try_load_module(pkg_name)
    return (
        pkg_module.__version__ if hasattr(pkg_module, "__version__") else None
    )


def execute_clone_tasks(
    repo_names: List[str], api: plug.API, cwd: Optional[pathlib.Path] = None
) -> Mapping[str, List[plug.Result]]:
    """Execute clone tasks, if there are any, and return the results.

    Args:
        repo_names: Names of the repositories to execute clone tasks on.
        api: An instance of the platform API.
        cwd: Directory in which to find the repos.
    Returns:
        A mapping from repo name to hook result.
    """
    tasks = plug.manager.hook.clone_task() + _wrap_act_on_cloned_repo()
    return _execute_tasks(repo_names, tasks, api, cwd)


def execute_setup_tasks(
    repo_names: List[str], api: plug.API, cwd: Optional[pathlib.Path] = None
) -> Mapping[str, List[plug.Result]]:
    """Execute setup tasks, if there are any, and return the results.

    Args:
        repo_names: Names of the repositories to execute setup tasks on.
        api: An instance of the platform API.
        cwd: Directory in which to find the repos.
    Returns:
        A mapping from repo name to hook result.
    """
    tasks = plug.manager.hook.setup_task()
    return _execute_tasks(repo_names, tasks, api, cwd)


def _execute_tasks(
    repo_names: List[str],
    tasks: Iterable[plug.Task],
    api: plug.API,
    cwd: Optional[pathlib.Path],
) -> Mapping[str, List[plug.Result]]:
    """Execute plugin tasks on the provided repos."""
    if not tasks:
        return {}
    cwd = cwd or pathlib.Path(".")
    repo_paths = [f.absolute() for f in cwd.glob("*") if f.name in repo_names]

    with tempfile.TemporaryDirectory() as tmpdir:
        copies_root = pathlib.Path(tmpdir)
        repo_copies = []
        for path in repo_paths:
            copy = copies_root / path.name
            shutil.copytree(str(path), str(copy))
            repo_copies.append(copy)

        LOGGER.info("Executing tasks ...")
        results = collections.defaultdict(list)
        for path in repo_copies:
            LOGGER.info("Processing {}".format(path.name))

            for task in tasks:
                with _convert_task_exceptions(task):
                    res = task.act(path, api)
                if res:
                    results[path.name].append(res)
    return results


def _wrap_act_on_cloned_repo():
    """Wrap act_on_cloned_repo hook implementations in RepoBee Tasks."""
    tasks = []
    for p in plug.manager.get_plugins():
        if "act_on_cloned_repo" in dir(p):
            task = plug.Task(act=p.act_on_cloned_repo)
            tasks.append(task)
    return tasks


@contextlib.contextmanager
def _convert_task_exceptions(task):
    """Catch task exceptions and re-raise or convert into something more
    appropriate for the user. Only plug.PlugErrors will be let through without
    modification.
    """
    try:
        yield
    except plug.PlugError as exc:
        raise plug.PlugError(
            "A task from the module '{}' crashed: {}".format(
                task.act.__module__, str(exc)
            )
        )
    except Exception as exc:
        raise plug.PlugError(
            "A task from the module '{}' crashed unexpectedly. "
            "This is a bug, please report it to the plugin "
            "author.".format(task.act.__module__)
        ) from exc


def _handle_deprecation():
    """Emit warnings if any deprecated hooks are used."""
    deprecated_hooks = plug.deprecated_hooks()
    deprecated_hook_names = deprecated_hooks.keys()
    for p in plug.manager.get_plugins():
        for member in dir(p):
            if member in deprecated_hook_names:
                deprecation = deprecated_hooks[member]
                msg = (
                    "A plugin from the module '{}' is using the "
                    "deprecated '{}' hook, which will stop being supported as "
                    "of RepoBee {}.".format(
                        p.__module__ if "__module__" in dir(p) else p.__name__,
                        member,
                        deprecation.remove_by_version,
                    )
                )
                if deprecation.replacement:
                    msg += " '{}' should be used instead.".format(
                        deprecation.replacement
                    )
                LOGGER.warning(msg)
