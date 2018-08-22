__version__ = '0.1.1'
__author__ = 'Simon Larsén'

from repomate.pygithub_wrapper import PyGithubWrapper as APIWrapper

from repomate import plugin


def _initialize_plugins():
    """Load and register plugins."""
    plug_modules = plugin.load_plugin_modules()
    plugin.register_plugins(plug_modules)


_initialize_plugins()
