import argparse
import itertools

from typing import List, Tuple, Union, Iterator

from repobee_plug import exceptions
from repobee_plug import _corehooks
from repobee_plug import _exthooks
from repobee_plug import _containers
from repobee_plug import cli

from repobee_plug.cli.args import Option, MutuallyExclusiveGroup

_HOOK_METHODS = {
    key: value
    for key, value in itertools.chain(
        _exthooks.CloneHook.__dict__.items(),
        _exthooks.SetupHook.__dict__.items(),
        _exthooks.ConfigHook.__dict__.items(),
        _corehooks.PeerReviewHook.__dict__.items(),
        _corehooks.APIHook.__dict__.items(),
    )
    if callable(value) and not key.startswith("_")
}


class _PluginMeta(type):
    """Metaclass used for converting methods with appropriate names into
    hook methods. It ensures that all public methods have the name of a hook
    method.

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
        if cli.Command in bases or cli.CommandExtension in bases:
            attrdict = _process_cli_plugin(bases, attrdict)

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
            raise exceptions.HookNameError(
                "public method(s) with non-hook name: {}".format(
                    ", ".join(method_names - hook_names)
                )
            )

    @staticmethod
    def _extract_public_methods(attrdict):
        return {
            key: value
            for key, value in attrdict.items()
            if callable(value)
            and not key.startswith("_")
            and key not in ["command", "attach_options"]
        }


def _process_cli_plugin(bases, attrdict) -> dict:
    """Process a CLI plugin, generate its hook functions, and return a new
    attrdict with all attributes set correctly.
    """
    attrdict_copy = dict(attrdict)  # copy to avoid mutating original
    if cli.Command in bases and cli.CommandExtension in bases:
        raise exceptions.PlugError(
            "A plugin cannot be both a Command and a CommandExtension"
        )

    if cli.Command in bases:
        if "__settings__" not in attrdict_copy:
            attrdict_copy["__settings__"] = cli.command_settings()
    elif cli.CommandExtension in bases:
        if "__settings__" not in attrdict_copy:
            raise exceptions.PlugError(
                "CommandExtension must have a '__settings__' attribute"
            )

    handle_processed_args = _generate_handle_processed_args_func()
    attrdict_copy[handle_processed_args.__name__] = handle_processed_args
    attrdict_copy["attach_options"] = _attach_options

    configurable_argnames = list(_get_configurable_arguments(attrdict))
    if configurable_argnames:

        def get_configurable_args(self) -> _containers.ConfigurableArguments:
            return _containers.ConfigurableArguments(
                config_section_name=self.__settings__.config_section_name
                or self.plugin_name,
                argnames=list(
                    _get_configurable_arguments(self.__class__.__dict__)
                ),
            )

        attrdict_copy[get_configurable_args.__name__] = get_configurable_args

    return attrdict_copy


def _get_configurable_arguments(attrdict: dict) -> List[str]:
    """Returns a list of configurable argument names."""
    cli_args = _extract_flat_cli_options(attrdict)
    return [
        arg_name
        for arg_name, arg in cli_args
        if hasattr(arg, "configurable") and getattr(arg, "configurable")
    ]


def _extract_cli_options(
    attrdict,
) -> List[Tuple[str, Union[Option, MutuallyExclusiveGroup]]]:
    """Returns any members that are CLI options as a list of tuples on the form
    (member_name, option).
    """
    return [
        (key, value)
        for key, value in attrdict.items()
        if cli.is_cli_arg(value)
    ]


def _extract_flat_cli_options(
    attrdict,
) -> Iterator[Tuple[str, Union[Option, MutuallyExclusiveGroup]]]:
    """Like _extract_cli_options, but flattens nested options such as mutex
    groups.
    """
    cli_args = _extract_cli_options(attrdict)
    return itertools.chain.from_iterable(map(_flatten_arg, cli_args))


def _attach_options(self, config, show_all_opts, parser):
    parser = (
        parser
        if not isinstance(self, cli.CommandExtension)
        else parser.add_argument_group(
            title=self.plugin_name,
            description=f"Arguments for the {self.plugin_name} plugin",
        )
    )
    config_name = self.__settings__.config_section_name or self.plugin_name
    config_section = dict(config[config_name]) if config_name in config else {}

    opts = _extract_cli_options(self.__class__.__dict__)

    for (name, opt) in opts:
        configured_value = config_section.get(name)
        if configured_value and not (
            hasattr(opt, "configurable") and opt.configurable
        ):
            raise exceptions.PlugError(
                f"Plugin '{self.plugin_name}' does not allow "
                f"'{name}' to be configured"
            )
        _add_option(name, opt, configured_value, show_all_opts, parser)

    return parser


def _generate_handle_processed_args_func():
    def handle_processed_args(self, args):
        self.args = args
        flattened_args = _extract_flat_cli_options(self.__class__.__dict__)

        for name, arg in flattened_args:
            dest = (
                name
                if "dest" not in arg.argparse_kwargs
                else arg.argparse_kwargs["dest"]
            )
            if dest in args:
                parsed_arg = getattr(args, dest)
                setattr(self, dest, parsed_arg)

    return handle_processed_args


def _flatten_arg(arg_tup):
    name, arg = arg_tup
    assert cli.is_cli_arg(arg)

    if isinstance(arg, MutuallyExclusiveGroup):
        return itertools.chain.from_iterable(map(_flatten_arg, arg.options))
    else:
        return [arg_tup]


def _add_option(
    name: str,
    opt: Union[Option, MutuallyExclusiveGroup],
    configured_value: str,
    show_all_opts: bool,
    parser: Union[argparse.ArgumentParser, argparse._MutuallyExclusiveGroup],
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
    kwargs = dict(opt.argparse_kwargs or {})

    if opt.converter:
        kwargs["type"] = opt.converter

    kwargs["help"] = (
        argparse.SUPPRESS
        if (configured_value and not show_all_opts)
        else opt.help or ""
    )

    if opt.argument_type in [cli.ArgumentType.OPTION, cli.ArgumentType.FLAG]:
        if opt.short_name:
            args.append(opt.short_name)

        if opt.long_name:
            args.append(opt.long_name)
        else:
            args.append(f"--{name.replace('_', '-')}")

        kwargs["dest"] = name
        if not opt.argument_type == cli.ArgumentType.FLAG:
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
