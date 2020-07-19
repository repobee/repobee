import argparse
import collections

from repobee_plug import _exceptions
from repobee_plug import _corehooks
from repobee_plug import _exthooks
from repobee_plug import _containers

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
    hook methods.

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
            if callable(value)
            and not key.startswith("_")
            and key != "action_callback"
        }


opt = collections.namedtuple(
    "opt",
    [
        "short_name",
        "long_name",
        "configurable",
        "help",
        "description",
        "converter",
        "required",
        "default",
        "argparse_kwargs",
    ],
)
opt.__new__.__defaults__ = (None,) * len(opt._fields)


class _ActionMeta(_PluginMeta):
    def __new__(cls, name, bases, attrdict):
        opts = []
        for key, value in attrdict.items():
            if isinstance(value, opt):
                argparse_args = []
                argparse_kwargs = value.argparse_kwargs or {}

                if value.short_name:
                    argparse_args.append(value.short_name)

                if value.long_name:
                    argparse_args.append(value.long_name)
                else:
                    argparse_args.append(f"--{key.replace('_', '-')}")

                if value.converter:
                    argparse_kwargs["type"] = value.converter

                for kwarg_key in "required default help description".split():
                    kwarg_val = getattr(value, kwarg_key)
                    if kwarg_val:
                        argparse_kwargs[kwarg_key] = kwarg_val

                argparse_kwargs["dest"] = key

                opts.append((argparse_args, argparse_kwargs))

        if opts:
            category = attrdict["__category__"]
            action_name = attrdict["__action_name__"]

            def create_extension_command(self):
                def create_parser(config, show_all_opts):
                    parser = _containers.ExtensionParser()

                    config_section = (
                        dict(config[self.plugin_name])
                        if self.plugin_name in config
                        else {}
                    )

                    for (args, kwargs) in opts:
                        dest = kwargs["dest"]
                        is_configured = dest in config_section

                        kwargs["required"] = (
                            not is_configured and kwargs["required"]
                        )
                        kwargs["help"] = (
                            argparse.SUPPRESS
                            if (is_configured and not show_all_opts)
                            else kwargs["help"]
                        )
                        if is_configured:
                            kwargs["default"] = config_section[dest]

                        parser.add_argument(*args, **kwargs)
                    return parser

                return _containers.ExtensionCommand(
                    parser=create_parser,
                    name=action_name,
                    help="Yay",
                    description="Yay",
                    callback=self.action_callback,
                    category=category,
                )

            # add the extension command
            attrdict["create_extension_command"] = create_extension_command

        return super().__new__(cls, name, bases, attrdict)


class Plugin(metaclass=_ActionMeta):
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
