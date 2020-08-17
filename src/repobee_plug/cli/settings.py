"""Settings for declarative command line extensions."""
import collections

from typing import Optional, Union, List

from repobee_plug import _containers
from repobee_plug.cli.categorization import Category, Action


CommandSettings = collections.namedtuple(
    "CommandSettings",
    [
        "action",
        "category",
        "help",
        "description",
        "base_parsers",
        "config_section_name",
    ],
)


CommandExtensionSettings = collections.namedtuple(
    "CommandExtensionSettings", ["actions", "config_section_name"]
)


def command_settings(
    action: Optional[Union[str, Action]] = None,
    category: Optional[Category] = None,
    help: str = "",
    description: str = "",
    base_parsers: Optional[List[_containers.BaseParser]] = None,
    config_section_name: Optional[str] = None,
) -> CommandSettings:
    """Create a settings object for a :py:class:`Command`.

    Example usage:

    .. code-block:: python
        :caption: ext.py

        import repobee_plug as plug

        class Ext(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(
                action_name="hello",
                category=plug.cli.CoreCommand.config,
            )

            def command(self):
                print("Hello, world!")

    This can then be called with:

    .. code-block:: bash

        $ repobee -p ext.py config hello
        Hello, world!

    Args:
        action: The name of this command, or a :py:class:`Action` object that
            defines both category and action for the command. Defaults to the
            name of the plugin class.
        category: The category to place this command in. If not specified,
            then the command will be top-level (i.e. uncategorized). If
            ``action`` is an :py:class:`Action` (as opposed to a ``str``),
            then this argument is not allowed.
        help: A help section for the command. This appears when listing the
            help section of the command's category.
        description: A help section for the command. This appears when
            listing the help section for the command itself.
        base_parsers: A list of base parsers to add to the command.
        config_section_name: The name of the configuration section the
            command should look for configurable options in. Defaults
            to the name of the plugin the command is defined in.
    Returns:
        A settings object used internally by RepoBee.
    """
    if isinstance(action, Action):
        if category:
            raise TypeError(
                "argument 'category' not allowed when argument 'action' is an "
                "Action object"
            )
        category = action.category

    return CommandSettings(
        action=action,
        category=category,
        help=help,
        description=description,
        base_parsers=base_parsers,
        config_section_name=config_section_name,
    )


def command_extension_settings(
    actions: List["Action"], config_section_name: Optional[str] = None
) -> CommandExtensionSettings:
    """Settings for a :py:class:`CommandExtension`.

    Args:
        actions: A list of actions to extend.
        config_section_name: Name of the configuration section that the
            command extension will fetch configuration values from.
            Defaults to the name of the plugin in which the extension is
            defined.
    Returns:
        A wrapper object for settings.
    """

    if not actions:
        raise ValueError(
            f"argument 'actions' must be a non-empty list: {actions}"
        )
    return CommandExtensionSettings(
        actions=actions, config_section_name=config_section_name
    )
