import argparse
import daiquiri
import functools

from typing import List, Tuple, Callable, Mapping, Any, Union

from repobee_plug import _exceptions
from repobee_plug import _corehooks
from repobee_plug import _exthooks
from repobee_plug import _containers
from repobee_plug import cli

from repobee_plug.cli.args import Option, MutuallyExclusiveGroup

LOGGER = daiquiri.getLogger(__name__)

_HOOK_METHODS = {
    key: value
    for key, value in [
        *_exthooks.CloneHook.__dict__.items(),
        *_corehooks.PeerReviewHook.__dict__.items(),
        *_corehooks.APIHook.__dict__.items(),
        *_exthooks.ExtensionCommandHook.__dict__.items(),
        *_exthooks.TaskHooks.__dict__.items(),
    ]
    if callable(value) and not key.startswith("_")
}


class _PluginMeta(type):
    """Metaclass used for converting methods with appropriate names into
    hook methods. It also enables the declarative style of extension commands
    by automatically implementing the ``create_extension_command`` hook
    for any inheriting class that declares CLI-related members.

    Also ensures that all public methods have the name of a hook method.

    Checking signatures is handled by pluggy on registration.
    """

    def __new__(cls, name, bases, attrdict):
        """Check that all public methods have hook names, convert to hook
        methods and return a new instance of the class. If there are any
        public methods that have non-hook names,
        :py:function:`repobee_plug.exception.HookNameError` is raised.

        Checking signatures is delegated to ``pluggy`` during registration of
        the hook.
        """
        if cli.Command in bases and cli.CommandExtension in bases:
            raise _exceptions.PlugError(
                "A plugin cannot be both a Command and a CommandExtension"
            )

        if cli.Command in bases:
            ext_cmd_func = _generate_command_func(attrdict)
            attrdict[ext_cmd_func.__name__] = ext_cmd_func
        elif cli.CommandExtension in bases:
            if "__settings__" not in attrdict:
                raise _exceptions.PlugError(
                    "CommandExtension must have a '__settings__' attribute"
                )
            ext_cmd_func = _generate_command_extension_func()
            attrdict[ext_cmd_func.__name__] = ext_cmd_func

        methods = cls._extract_public_methods(attrdict)
        cls._check_names(methods)
        hooked_methods = {
            name: _containers.hookimpl(method)
            for name, method in methods.items()
        }
        attrdict.update(hooked_methods)

        return super().__new__(cls, name, bases, attrdict)

    @staticmethod
    def _check_names(methods):
        hook_names = set(_HOOK_METHODS.keys())
        method_names = set(methods.keys())
        if not method_names.issubset(hook_names):
            raise _exceptions.HookNameError(
                "public method(s) with non-hook name: {}".format(
                    ", ".join(method_names - hook_names)
                )
            )

    @staticmethod
    def _extract_public_methods(attrdict):
        return {
            key: value
            for key, value in attrdict.items()
            if callable(value) and not key.startswith("_") and key != "command"
        }


def _extract_cli_options(
    attrdict,
) -> List[Tuple[str, Union[Option, MutuallyExclusiveGroup]]]:
    """Return any members that are CLI options as a list of tuples on the form
    (member_name, option). Other types of CLI arguments, such as positionals,
    are converted to :py:class:`~cli.Option`s.
    """
    return [
        (key, value)
        for key, value in attrdict.items()
        if isinstance(value, (Option, MutuallyExclusiveGroup))
    ]


def _generate_command_extension_func() -> Callable:
    """Generate an implementation of the ``create_extension_command`` that
    returns an extension to an existing command.
    """

    def create_extension_command(self):
        settings = self.__settings__
        if settings.config_section_name:
            self.__config_section__ = settings.config_section_name

        return _containers.ExtensionCommand(
            parser=functools.partial(_attach_options, plugin=self),
            # FIXME support more than one action
            name=settings.actions[0],
            callback=lambda: None,
            description=None,
            help=None,
        )

    return create_extension_command


def _attach_options(config, show_all_opts, parser, plugin: "Plugin"):
    config_name = (
        getattr(plugin, "__config_section__", None) or plugin.plugin_name
    )
    config_section = dict(config[config_name]) if config_name in config else {}

    opts = _extract_cli_options(plugin.__class__.__dict__)
    for (name, opt) in opts:
        configured_value = config_section.get(name)
        if configured_value and not (
            hasattr(opt, "configurable") and opt.configurable
        ):
            raise _exceptions.PlugError(
                f"Plugin '{plugin.plugin_name}' does not allow "
                f"'{name}' to be configured"
            )
        _add_option(name, opt, configured_value, show_all_opts, parser)

    return parser


def _generate_command_func(attrdict: Mapping[str, Any]) -> Callable:
    """Generate an implementation of the ``create_extension_command`` hook
    function based on the declarative-style extension command class.
    """

    def create_extension_command(self):
        settings = attrdict.get("__settings__") or cli.command_settings()
        if settings.config_section_name:
            self.__config_section__ = settings.config_section_name

        return _containers.ExtensionCommand(
            parser=functools.partial(_attach_options, plugin=self),
            name=settings.action
            or self.__class__.__name__.lower().replace("_", "-"),
            help=settings.help,
            description=settings.description,
            callback=self.command,
            category=settings.category,
            requires_api=settings.requires_api,
            requires_base_parsers=settings.base_parsers,
        )

    return create_extension_command


def _add_option(
    name: str,
    opt: Union[Option, MutuallyExclusiveGroup],
    configured_value: str,
    show_all_opts: bool,
    parser: argparse.ArgumentParser,
) -> None:
    """Add an option to the parser based on the cli option."""
    if isinstance(opt, MutuallyExclusiveGroup):
        mutex_parser = parser.add_mutually_exclusive_group(
            required=opt.required
        )
        for (mutex_opt_name, mutex_opt) in opt.options:
            _add_option(
                mutex_opt_name,
                mutex_opt,
                configured_value,
                show_all_opts,
                mutex_parser,
            )
        return

    assert isinstance(opt, Option)
    args = []
    kwargs = opt.argparse_kwargs

    if opt.converter:
        kwargs["type"] = opt.converter

    kwargs["help"] = (
        argparse.SUPPRESS
        if (configured_value and not show_all_opts)
        else opt.help or ""
    )

    if opt.argument_type == cli.ArgumentType.OPTION:
        if opt.short_name:
            args.append(opt.short_name)

        if opt.long_name:
            args.append(opt.long_name)
        else:
            args.append(f"--{name.replace('_', '-')}")

        kwargs["dest"] = name
        # configured value takes precedence over default
        kwargs["default"] = configured_value or opt.default
        # required opts become not required if configured
        kwargs["required"] = not configured_value and opt.required
    elif opt.argument_type == cli.ArgumentType.POSITIONAL:
        args.append(name)

    parser.add_argument(*args, **kwargs)


class Plugin(metaclass=_PluginMeta):
    """This is a base class for plugin classes. For plugin classes to be picked
    up by RepoBee, they must inherit from this class.

    Public methods must be hook methods. If there are any public methods that
    are not hook methods, an error is raised on creation of the class. As long
    as the method has the correct name, it will be recognized as a hook method
    during creation. However, if the signature is incorrect, the plugin
    framework will raise a runtime exception once it is called. Private methods
    (i.e.  methods prefixed with ``_``) carry no restrictions.

    The signatures of hook methods are not checked until the plugin class is
    registered by the :py:const:`repobee_plug.manager` (an instance of
    :py:class:`pluggy.manager.PluginManager`). Therefore, when testing a
    plugin, it is a good idea to include a test where it is registered with the
    manager to ensure that it has the correct signatures.

    A plugin class is instantiated exactly once; when RepoBee loads the plugin.
    This means that any state that is stored in the plugin will be carried
    throughout the execution of a RepoBee command. This makes plugin classes
    well suited for implementing tasks that require command line options or
    configuration values, as well as for implementing extension commands.
    """

    def __init__(self, plugin_name: str):
        """
        Args:
            plugin_name: Name of the plugin that this instance belongs to.
        """
        self.plugin_name = plugin_name
