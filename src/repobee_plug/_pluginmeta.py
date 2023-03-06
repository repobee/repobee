import argparse
import shlex
import itertools
import inspect
import re

from typing import List, Tuple, Union, Iterator, Any, Optional, Callable

import repobee_plug.config
from repobee_plug import exceptions
from repobee_plug import _corehooks
from repobee_plug import _exthooks
from repobee_plug import cli
from repobee_plug.cli import base
from repobee_plug.cli.args import ConfigurableArguments
from repobee_plug.hook import hookimpl

from repobee_plug.cli.args import _Option, _MutuallyExclusiveGroup

_HOOK_METHODS = {
    key: value
    for key, value in itertools.chain(
        _corehooks.__dict__.items(), _exthooks.__dict__.items()
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
            name: hookimpl(method) for name, method in methods.items()
        }
        attrdict.update(hooked_methods)

        return super().__new__(cls, name, bases, attrdict)

    @staticmethod
    def _check_names(methods):
        hook_names = set(_HOOK_METHODS.keys())
        method_names = set(methods.keys())
        if not method_names.issubset(hook_names):
            raise exceptions.HookNameError(
                f"public method(s) with non-hook name: {', '.join(method_names - hook_names)}"
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
        settings = attrdict_copy.get("__settings__", cli.command_settings())
        attrdict_copy["__settings__"] = settings
        _check_base_parsers(settings.base_parsers or [], attrdict_copy)
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

        def get_configurable_args(self) -> ConfigurableArguments:
            return ConfigurableArguments(
                config_section_name=self.__settings__.config_section_name
                or self.__plugin_name__,
                argnames=list(
                    _get_configurable_arguments(self.__class__.__dict__)
                ),
            )

        attrdict_copy[get_configurable_args.__name__] = get_configurable_args

    return attrdict_copy


def _check_base_parsers(
    base_parsers: List[base.BaseParser], attrdict: dict
) -> None:
    """Check that the base parser list fulfills all requirements."""
    if base.BaseParser.REPO_DISCOVERY in base_parsers:
        # the REPO_DISCOVERY parser requires both the STUDENTS parser and
        # the api argument to the command function, see
        # https://github.com/repobee/repobee/issues/716 for details
        if base.BaseParser.STUDENTS not in base_parsers:
            raise exceptions.PlugError(
                "REPO_DISCOVERY parser requires STUDENT parser"
            )
        elif "api" not in inspect.signature(attrdict["command"]).parameters:
            raise exceptions.PlugError(
                "REPO_DISCOVERY parser requires command function to use api "
                "argument"
            )


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
) -> List[Tuple[str, Union[_Option, _MutuallyExclusiveGroup]]]:
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
) -> Iterator[Tuple[str, Union[_Option, _MutuallyExclusiveGroup]]]:
    """Like _extract_cli_options, but flattens nested options such as mutex
    groups.
    """
    cli_args = _extract_cli_options(attrdict)
    return itertools.chain.from_iterable(map(_flatten_arg, cli_args))


def _attach_options(self, config: repobee_plug.config.Config, parser):
    parser = (
        parser
        if not isinstance(self, cli.CommandExtension)
        else parser.add_argument_group(
            title=self.__plugin_name__,
            description=f"Arguments for the {self.__plugin_name__} plugin",
        )
    )
    section_name = (
        self.__settings__.config_section_name or self.__plugin_name__
    )
    opts = _extract_cli_options(self.__class__.__dict__)

    def get_configured_value(opt_name: str, opt: _Option) -> Any:
        configured_value = config.get(section_name, opt_name)
        if configured_value and not getattr(opt, "configurable", None):
            raise exceptions.PlugError(
                f"Plugin '{self.__plugin_name__}' does not allow "
                f"'{opt_name}' to be configured"
            )

        return _pack_configured_value(opt, configured_value)

    for arg_name, opt in opts:
        if isinstance(opt, _MutuallyExclusiveGroup):
            _add_mutually_exclusive_group(
                opt,
                parser,
                get_configured_value,
            )
        else:
            configured_value = get_configured_value(arg_name, opt)
            _add_option(arg_name, opt, configured_value, parser)

    return parser


def _pack_configured_value(
    opt: _Option, configured_value: Optional[Any]
) -> Optional[Any]:
    if (
        configured_value
        and opt.argparse_kwargs
        and re.match(r"\+|\*|\d+", str(opt.argparse_kwargs.get("nargs")))
    ):
        individual_args = shlex.split(configured_value)
        converter = opt.converter if opt.converter else lambda x: x
        return tuple(map(converter, individual_args))
    else:
        return configured_value


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

    if isinstance(arg, _MutuallyExclusiveGroup):
        return itertools.chain.from_iterable(map(_flatten_arg, arg.options))
    else:
        return [arg_tup]


def _add_mutually_exclusive_group(
    mutex_group: _MutuallyExclusiveGroup,
    parser: argparse.ArgumentParser,
    get_configured_value: Callable[[str, _Option], Optional[Any]],
):
    has_configured_value = any(
        get_configured_value(opt_name, opt)
        for opt_name, opt in mutex_group.options
    )
    mutex_parser = parser.add_mutually_exclusive_group(
        required=mutex_group.required and not has_configured_value
    )

    for mutex_opt_name, mutex_opt in mutex_group.options:
        configured_value = get_configured_value(mutex_opt_name, mutex_opt)
        _add_option(
            mutex_opt_name,
            mutex_opt,
            configured_value,
            mutex_parser,
        )


def _add_option(
    name: str,
    opt: _Option,
    configured_value: Optional[Any],
    parser: Union[argparse.ArgumentParser, argparse._MutuallyExclusiveGroup],
) -> None:
    """Add an option to the parser based on the cli option."""
    if opt.argument_type == cli.args._ArgumentType.IGNORE:
        return

    args = []
    kwargs = dict(opt.argparse_kwargs or {})

    if opt.converter:
        kwargs["type"] = opt.converter

    kwargs["help"] = opt.help or ""

    if opt.argument_type in [
        cli.args._ArgumentType.OPTION,
        cli.args._ArgumentType.FLAG,
    ]:
        if opt.short_name:
            args.append(opt.short_name)

        assert isinstance(opt.long_name, str)
        args.append(opt.long_name)

        kwargs["dest"] = name
        if not opt.argument_type == cli.args._ArgumentType.FLAG:
            # configured value takes precedence over default
            kwargs["default"] = configured_value or opt.default
        # required opts become not required if configured
        kwargs["required"] = not configured_value and opt.required
    elif opt.argument_type == cli.args._ArgumentType.POSITIONAL:
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
        self.__plugin_name__ = plugin_name
