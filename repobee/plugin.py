"""Plugin system module.

Module containing plugin system utility functions and classes.

.. module:: plugin
    :synopsis: PLugin system utility functions and classes.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import importlib
from types import ModuleType
from typing import Union, List, Optional, Iterable

import daiquiri

from repobee import config
from repobee import exception

import repobee_plug as plug

LOGGER = daiquiri.getLogger(__file__)


def _plugin_qualname(plugin_name):
    return "{}.ext.{}".format(__package__, plugin_name)


def _external_plugin_qualname(plugin_name):
    return "{}_{}.{}".format(__package__, plugin_name, plugin_name)


DEFAULT_PLUGIN = "defaults"


def load_plugin_modules(
    config_file: Union[str, pathlib.Path] = config.DEFAULT_CONFIG_FILE,
    plugin_names: Iterable[str] = None,
) -> List[ModuleType]:
    """Load plugins that are specified in the config, as well as default
    plugins. Note that default plugins are always loaded first, such that
    they are either run last or overridden by plugins with firstresult=True
    (such as the default_peer_review plugin).

    Try to import first from :py:mod:`repobee.ext`, and then from
    ``repobee_<plugin>``. For example, if ``javac`` is listed as a plugin, the
    following imports will be attempted:

    .. code-block:: python

        # import nr 1
        from repobee.ext import javac

        # import nr 2
        from repobee_javac import javac

    Args:
        config_file: Path to the configuration file.
        plugin_names: A list of plugin names. Overrides the config file.

    Returns:
        a list of loaded modules.
    """
    loaded_modules = []
    plugin_names = [
        *(plugin_names or config.get_plugin_names(config_file) or []),
        # default plugin last so hooks are overridden by user-specified hooks
        DEFAULT_PLUGIN,
    ]
    if plugin_names == [DEFAULT_PLUGIN]:
        from .ext import defaults

        return [defaults]

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
