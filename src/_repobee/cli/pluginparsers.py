"""Functions for attaching plugin parsers."""
import argparse

from typing import List, Tuple

import repobee_plug as plug

from repobee_plug.cli import categorization

from _repobee.cli import argparse_ext


def add_plugin_parsers(
    subparsers: argparse._SubParsersAction,
    base_parsers: argparse_ext.BaseParsers,
    parsers_mapping: dict,
    config: plug.Config,
):
    """Add parsers defined by plugins."""
    command_plugins = [
        p
        for p in plug.manager.get_plugins()
        if isinstance(p, plug.cli.Command)
    ]
    for cmd in command_plugins:
        _attach_command(cmd, base_parsers, subparsers, parsers_mapping, config)

    command_extension_plugins = [
        p
        for p in plug.manager.get_plugins()
        if isinstance(p, plug.cli.CommandExtension)
    ]
    for cmd_ext in command_extension_plugins:
        for action in cmd_ext.__settings__.actions:
            parser = parsers_mapping[action]
            cmd_ext.attach_options(config=config, parser=parser)


def _attach_command(
    cmd: plug.cli.Command,
    base_parsers: argparse_ext.BaseParsers,
    subparsers: argparse._SubParsersAction,
    parsers_mapping: dict,
    config: plug.Config,
) -> None:
    category, action, is_category_action = _resolve_category_and_action(cmd)

    parents = _compose_parent_parsers(cmd, base_parsers)

    if category and category not in parsers_mapping and not is_category_action:
        parsers_mapping[category] = _create_category_parser(
            category, subparsers
        )

    assert action not in parsers_mapping, f"{action} already exists"

    settings = cmd.__settings__
    ext_parser = _create_action_parser(
        cmd=cmd,
        action=action,
        is_category_action=is_category_action,
        parsers_mapping=parsers_mapping,
        subparsers=subparsers,
        parents=parents,
    )
    cmd.attach_options(config=config, parser=ext_parser)

    settings_dict = settings._asdict()
    settings_dict.update(dict(action=action, category=category))
    cmd.__settings__ = settings.__class__(**settings_dict)

    parsers_mapping[action] = ext_parser


def _resolve_category_and_action(
    cmd: plug.cli.Command,
) -> Tuple[categorization.Category, categorization.Action, bool]:
    settings = cmd.__settings__
    category = (
        settings.action.category
        if isinstance(settings.action, categorization.Action)
        else settings.category
    )
    action = settings.action or cmd.__class__.__name__.lower().replace(
        "_", "-"
    )

    if isinstance(action, str):
        is_category_action = False
        if not category:
            is_category_action = True
            category = plug.cli.category(name=action, action_names=[action])
        return (
            category,
            (
                category[action]
                if category and action in category
                else categorization.Action(name=action, category=category)
            ),
            is_category_action,
        )
    else:
        return category, action, False


def _compose_parent_parsers(
    cmd: plug.cli.Command, bases: argparse_ext.BaseParsers
):
    parents = []
    bp = plug.BaseParser
    req_parsers = cmd.__settings__.base_parsers or []
    if cmd.__requires_api__() or bp.BASE in req_parsers:
        parents.append(bases.base_parser)
    if bp.STUDENTS in req_parsers:
        parents.append(bases.student_parser)
    if bp.TEMPLATE_ORG in req_parsers:
        parents.append(bases.template_org_parser)

    if bp.REPO_DISCOVERY in req_parsers:
        parents.append(bases.repo_discovery_parser)
    elif bp.ASSIGNMENTS in req_parsers:
        parents.append(bases.repo_name_parser)

    return parents


def _create_category_parser(
    category: categorization.Category, subparsers: argparse._SubParsersAction
) -> argparse._SubParsersAction:
    category_cmd = subparsers.add_parser(
        name=category.name,
        help=category.help,
        description=category.description,
    )
    category_parser = category_cmd.add_subparsers(
        dest=argparse_ext.ACTION_DEST
    )
    category_parser.required = True
    return category_parser


def _create_action_parser(
    cmd: plug.cli.Command,
    action: categorization.Action,
    is_category_action: bool,
    parsers_mapping: dict,
    subparsers: argparse._SubParsersAction,
    parents: List[argparse.ArgumentParser],
):
    settings = cmd.__settings__
    ext_parser = (
        parsers_mapping.get(action.category) or subparsers
    ).add_parser(
        action.name,
        help=settings.help,
        description=settings.description,
        parents=parents,
        formatter_class=argparse_ext.OrderedFormatter,
    )

    try:
        argparse_ext.add_debug_args(ext_parser)
    except argparse.ArgumentError:
        pass

    _add_metainfo_args(
        ext_parser=ext_parser,
        action=action,
        cmd=cmd,
        is_category_action=is_category_action,
    )

    return ext_parser


def _add_metainfo_args(
    ext_parser: argparse.ArgumentParser,
    action: categorization.Action,
    cmd: plug.cli.Command,
    is_category_action: bool,
) -> None:
    try:
        # this will fail if we are adding arguments to an existing command
        ext_parser.add_argument(
            "--repobee-action",
            action="store_const",
            help=argparse.SUPPRESS,
            const=action.name,
            default=action.name,
            dest="action",
        )
        # This is a little bit of a dirty trick. It allows us to easily
        # find the associated extension command when parsing the arguments.
        ext_parser.add_argument(
            "--repobee-extension-command",
            action="store_const",
            help=argparse.SUPPRESS,
            const=cmd,
            default=cmd,
            dest="_extension_command",
        )
    except argparse.ArgumentError:
        pass

    if is_category_action:
        # category is not specified, so it's a category-action
        ext_parser.add_argument(
            "--repobee-category",
            action="store_const",
            help=argparse.SUPPRESS,
            const=action.category,
            default=action.category,
            dest="category",
        )
