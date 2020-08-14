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
import pkgutil
import pathlib
import importlib
import os
from types import ModuleType
from typing import List, Optional, Iterable, Mapping, Union, Callable


import _repobee
import _repobee.ext.defaults
import _repobee.ext.dist
import _repobee.distinfo
from _repobee import exception

import repobee_plug as plug


def _plugin_qualname(plugin_name):
    return "{}.ext.{}".format(_repobee._internal_package_name, plugin_name)


def _external_plugin_qualname(plugin_name):
    return "{}_{plugin_name}.{plugin_name}".format(
        _repobee._external_package_name, plugin_name=plugin_name
    )


def load_plugin_modules(
    plugin_names: Iterable[str],
    allow_qualified: bool = False,
    allow_filepath: bool = False,
) -> List[ModuleType]:
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

        # import nr 3 (only if allow_qualified)
        import javac

        # import nr 4 (only if allow_filepath)
        # Dynamically import using the name as a filepath

    Args:
        plugin_names: A list of plugin names.
        allow_qualified: Allow the plugin to be specified by a qualified name.
        allow_filepath: Allows the plugin to be specified as a filepath.
    Returns:
        a list of loaded modules.
    """
    loaded_modules = []
    plug.log.debug("Loading plugins: " + ", ".join(plugin_names))

    for name in plugin_names:
        plug_mod = (
            _try_load_module(_plugin_qualname(name))
            or _try_load_module(_external_plugin_qualname(name))
            or (allow_qualified and _try_load_module(name))
            or (allow_filepath and _try_load_module_from_filepath(name))
        )
        if not plug_mod:
            msg = "failed to load plugin module " + name
            raise exception.PluginLoadError(msg)
        loaded_modules.append(plug_mod)
    return loaded_modules


def _try_load_module_from_filepath(path: str) -> Optional[ModuleType]:
    """Try to load a module from the specified filepath.

    Adapted from code by Sebastian Rittau (https://stackoverflow.com/a/67692).

    Args:
        path: A path to a Python module.
    Returns:
        The module if loaded successfully, or None if there was no module at
        the path.
    """
    package_name = plug.fileutils.hash_path(path)
    module_name = pathlib.Path(path).stem
    qualname = f"{package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(qualname, path)
    if not spec:
        return None

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod


def _try_load_module(qualname: str) -> Optional[ModuleType]:
    """Try to load a module.

    Args:
        qualname: Qualified name of the module.

    Returns:
        the module if loaded properly, None otherwise
    """
    try:
        return importlib.import_module(qualname)
    except ModuleNotFoundError:
        return None


def register_plugins(modules: List[ModuleType]) -> List[object]:
    """Register the namespaces of the provided modules, and any plug.Plugin
    instances in them. Registers modules in reverse order as they are
    run in LIFO order.

    Args:
        modules: A list of modules.
    Returns:
        A list of registered modules and and plugin class instances.
    """
    assert all([isinstance(mod, ModuleType) for mod in modules])

    registered = []
    for module in reversed(modules):  # reverse because plugins are run LIFO
        plugin_name = module.__name__.split(".")[-1]
        plug.manager.register(module)
        registered.append(module)

        for value in module.__dict__.values():
            if (
                isinstance(value, type)
                and issubclass(value, plug.Plugin)
                and value != plug.Plugin
            ):
                obj = value(plugin_name)
                plug.manager.register(obj)
                registered.append(obj)

    _handle_deprecation()
    return registered


def unregister_all_plugins() -> None:
    """Unregister all currently registered plugins."""
    for p in plug.manager.get_plugins():
        plug.manager.unregister(p)


def try_register_plugin(
    plugin_module: ModuleType, *plugin_classes: List[type]
) -> None:
    """Attempt to register a plugin module and then immediately unregister it.

    .. important::
        This is a convenience method for sanity checking plugins, and should
        only be called in test suites. It's not for production use.

    This convenience method can be used to sanity check plugins by registering
    them with RepoBee. If they have incorrectly defined hooks, this will be
    discovered only when registering.

    As an example, assume that we have a plugin module with a single (useless)
    plugin class in it, like this:

    .. code-block:: python
        :caption: useless.py

        import repobee_plug as plug

        class Useless(plug.Plugin):
            \"\"\"This plugin does nothing!\"\"\"

    We want to make sure that both the ``useless`` module and the ``Useless``
    plugin class are registered correctly, and for that we can write some
    simple code like this.

    .. code-block:: python
        :caption: Example test case to check registering

        import repobee
        # assuming that useless is defined in the external plugin
        # repobee_useless
        from repobee_useless import useless

        def test_register_useless_plugin():
            repobee.try_register_plugin(useless, useless.Useless)

    Args:
        plugin_module: A plugin module.
        plugin_classes: If the plugin contains any plugin classes (i.e. classes
            that extend :py:class:`repobee_plug.Plugin`), then these must be
            provided here. Otherwise, this option should not be provided.
    Raises:
        :py:class:`repobee_plug.PlugError` if the module cannot be registered,
        or if the contained plugin classes does not match
        plugin_classes.
    """
    expected_plugin_classes = set(plugin_classes or [])
    newly_registered = register_plugins([plugin_module])
    for reg in newly_registered:
        plug.manager.unregister(reg)

    registered_modules = [
        reg for reg in newly_registered if isinstance(reg, ModuleType)
    ]
    registered_classes = {
        cl.__class__ for cl in newly_registered if cl not in registered_modules
    }

    assert len(registered_modules) == 1, "Module was not registered"
    if expected_plugin_classes != registered_classes:
        raise plug.PlugError(
            f"Expected plugin classes {expected_plugin_classes}, "
            f"got {registered_classes}"
        )


def initialize_plugins(
    plugin_names: List[str] = None,
    allow_qualified: bool = False,
    allow_filepath: bool = False,
) -> List[Union[ModuleType, type]]:
    """Load and register plugins.

    Args:
        plugin_names: An optional list of plugin names that overrides the
            configuration file's plugins.
        allow_qualified: Allows the plugin names to be qualified.
        allow_filepath: Allows the plugin to be specified as a filepath.
    Returns:
        A list of registered modules and classes.
    Raises:
        :py:class:`_repobee.exception.PluginLoadError`
    """
    if not allow_filepath:
        _check_no_filepaths(plugin_names)
    if not allow_qualified:
        _check_no_qualified_names(plugin_names)

    registered_plugins = plug.manager.get_plugins()
    plug_modules = [
        p
        for p in load_plugin_modules(
            plugin_names, allow_qualified, allow_filepath
        )
        if p not in registered_plugins
    ]
    registered = register_plugins(plug_modules)
    return registered


def _is_filepath(name: str) -> bool:
    return os.pathsep in name or os.path.exists(name)


def _check_no_filepaths(names: List[str]):
    filepaths = [name for name in names if _is_filepath(name)]
    if filepaths:
        raise exception.PluginLoadError(f"Filepaths not allowed: {filepaths}")


def _check_no_qualified_names(names: List[str]):
    qualified_names = [
        name for name in names if "." in name and not _is_filepath(name)
    ]
    if qualified_names:
        raise exception.PluginLoadError(
            f"Qualified names not allowed: {qualified_names}"
        )


def resolve_plugin_version(plugin_module: ModuleType) -> Optional[str]:
    """Return the version of this plugin. Tries to resolve the version by
    first checking if the plugin module itself has a ``__version__``
    attribute, and then the top level package.

    Args:
        plugin_module: A plugin module.
    Returns:
        The version if found, otherwise None.
    """
    if hasattr(plugin_module, "__version__"):
        return plugin_module.__version__

    pkg_name = plugin_module.__package__.split(".")[0]
    pkg_module = _try_load_module(pkg_name)
    return (
        pkg_module.__version__ if hasattr(pkg_module, "__version__") else None
    )


def is_default_plugin(module: ModuleType) -> Optional[str]:
    """Check if the provided module is a default module.

    Args:
        module: A Python module.
    Returns:
        True iff the provided module is a default plugin.
    """
    return module.__package__ == _repobee.ext.defaults.__name__


def initialize_default_plugins() -> None:
    """Initialize the default plugin modules."""
    default_plugin_qualnames = get_qualified_module_names(
        _repobee.ext.defaults
    )
    initialize_plugins(default_plugin_qualnames, allow_qualified=True)


def initialize_dist_plugins() -> None:
    """Initialize the distribution plugin modules."""
    if not _repobee.distinfo.DIST_INSTALL:
        raise exception.PluginLoadError(
            "Dist plugins can only be loaded with installed RepoBee"
        )
    dist_plugin_qualnames = get_qualified_module_names(_repobee.ext.dist)
    initialize_plugins(dist_plugin_qualnames, allow_qualified=True)


def get_qualified_module_names(pkg: ModuleType) -> List[str]:
    """Return a list of all python modules in the given package. Only considers
    the modules directly in this package, and not in subpackages.

    Args:
        pkg: The package to resolve modules in.
    Returns:
        All modules in the given package.
    """
    return [f"{pkg.__name__}.{name}" for name in get_module_names(pkg)]


def get_module_names(pkg: ModuleType) -> List[str]:
    """Get the unqualified module names from the given package.

    Args:
        pkg: The package to resolve modules in.
    Returns:
        All modules in the given package.
    """
    return [
        name
        for file_finder, name, _ in pkgutil.iter_modules(pkg.__path__)
        # only include modules (i.e. files), not subpackages
        if (pathlib.Path(file_finder.path) / (name + ".py")).is_file()
    ]


def execute_clone_tasks(
    repos: Iterable[plug.StudentRepo],
    api: plug.PlatformAPI,
    cwd: Optional[pathlib.Path] = None,
) -> Mapping[str, List[plug.Result]]:
    """Execute clone tasks, if there are any, and return the results.

    Args:
        repo_names: Names of the repositories to execute clone tasks on.
        api: An instance of the platform API.
        cwd: Directory in which to find the repos.
    Returns:
        A mapping from repo name to hook result.
    """
    return _execute_tasks(repos, plug.manager.hook.post_clone, api, cwd)


def execute_setup_tasks(
    repos: Iterable[plug.TemplateRepo],
    api: plug.PlatformAPI,
    cwd: Optional[pathlib.Path] = None,
) -> Mapping[str, List[plug.Result]]:
    """Execute setup tasks, if there are any, and return the results.

    Args:
        repos: Template repos.
        api: An instance of the platform API.
        cwd: Directory in which to find the repos.
    Returns:
        A mapping from repo name to hook result.
    """
    return _execute_tasks(repos, plug.manager.hook.pre_setup, api, cwd)


def _execute_tasks(
    repos: List[Union[plug.StudentRepo, plug.TemplateRepo]],
    hook_function: Callable[
        [pathlib.Path, plug.PlatformAPI], Optional[plug.Result]
    ],
    api: plug.PlatformAPI,
    cwd: Optional[pathlib.Path],
) -> Mapping[str, List[plug.Result]]:
    """Execute plugin tasks on the provided repos."""
    cwd = cwd or pathlib.Path(".")

    with tempfile.TemporaryDirectory() as tmpdir:
        copies_root = pathlib.Path(tmpdir)
        repo_copies = []
        for repo in repos:
            copy_path = copies_root / plug.fileutils.hash_path(repo.path)
            shutil.copytree(repo.path, copy_path)
            repo_copies.append(repo.with_path(copy_path))

        plug.log.info("Executing tasks ...")
        results = collections.defaultdict(list)
        for repo in repo_copies:
            plug.log.info("Processing {}".format(repo.path.name))

            for result in hook_function(repo=repo, api=api):
                if result:
                    results[repo.path.name].append(result)
    return results


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
                plug.log.warning(msg)
