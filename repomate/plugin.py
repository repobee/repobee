"""Plugin system module.

Module containing plugin system utility functions and classes.

.. module:: plugin
    :synopsis: PLugin system utility functions and classes.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import importlib
from types import ModuleType
from typing import Union, List

import daiquiri

from repomate import config
from repomate import exception
from repomate import hookspec

LOGGER = daiquiri.getLogger(__file__)

PLUGIN_QUALNAME = lambda plugin_name: "{}.ext.{}".format(__package__, plugin_name)

# status messages
ERROR = "error"
WARNING = "warning"
SUCCESS = "success"


class Plugin:
    """Wrapper class for plugin classes. Used to dynamically detect plugin
    classes during plugin registration. Any plugin class must be decorated
    with this class.
    """

    def __init__(self, class_):
        assert isinstance(class_, type)  # sanity check
        self._class = class_

    def __call__(self, *args, **kwargs):
        return self._class(*args, **kwargs)


def load_plugin_modules(
        config_file: Union[str, pathlib.Path] = config.DEFAULT_CONFIG_FILE
) -> List[ModuleType]:
    """Load plugins that are specified in the config.
    
    Args:

    Returns:
        a list of loaded modules.
    """
    loaded_modules = []

    for name in config.get_plugin_names(config_file):
        try:
            plugin = importlib.import_module(PLUGIN_QUALNAME(name))
            loaded_modules.append(plugin)
        except ImportError as exc:
            # ImportError in 3.5, ModuleNotFoundError in 3.6+
            # using ImportError for compatability
            LOGGER.error(str(exc))
            msg = "failed to load plugin module " + name
            raise exception.PluginError(msg)

    LOGGER.info("loaded modules {}".format(
        [mod.__name__ for mod in loaded_modules]))

    return loaded_modules


def register_plugins(modules: List[ModuleType]) -> None:
    """Register the namespaces of the provided modules, and any Plugin
    instances in them. Registers modules in reverse order as they are
    run in FIFO order.
    
    Args:
        modules: A list of modules.
    """
    assert all([isinstance(mod, ModuleType) for mod in modules])
    for module in reversed(modules):  # reverse because plugins are run FIFO
        hookspec.pm.register(module)
        LOGGER.info("registered {}".format(module.__name__))
        for key, value in module.__dict__.items():
            if isinstance(value, Plugin):
                hookspec.pm.register(value())
                LOGGER.info("registered class {}".format(key))
