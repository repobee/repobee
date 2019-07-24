"""Plugin system module.

Module containing plugin system utility functions and classes.

.. module:: plugin
    :synopsis: PLugin system utility functions and classes.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import importlib
from types import ModuleType
from typing import List, Optional, Iterable

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
            raise exception.PluginError(msg)
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
    for module in reversed(modules):  # reverse because plugins are run FIFO
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
    plug_modules = load_plugin_modules(plugin_names=plugin_names)
    register_plugins(plug_modules)


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
