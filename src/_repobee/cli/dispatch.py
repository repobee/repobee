"""Module dispatching CLI commands to RepoBee's internal.

This module essentially translates parsed and processed arguments from the
CLI into commands for RepoBee's core.

.. module:: dispatch
    :synopsis: Command dispatcher for the CLI.

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
from typing import Optional, List, Mapping

import repobee_plug as plug

from _repobee import command, exception, formatters, util
from _repobee.cli.mainparser import (
    SETUP_PARSER,
    UPDATE_PARSER,
    OPEN_ISSUE_PARSER,
    CLOSE_ISSUE_PARSER,
    MIGRATE_PARSER,
    CLONE_PARSER,
    VERIFY_PARSER,
    LIST_ISSUES_PARSER,
    ASSIGN_REVIEWS_PARSER,
    PURGE_REVIEW_TEAMS_PARSER,
    SHOW_CONFIG_PARSER,
    CHECK_REVIEW_PROGRESS_PARSER,
    CREATE_TEAMS_PARSER,
    LOGGER,
)


def dispatch_command(
    args: argparse.Namespace,
    api: plug.API,
    config_file: pathlib.Path,
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
):
    """Handle parsed CLI arguments and dispatch commands to the appropriate
    functions. Expected exceptions are caught and turned into SystemExit
    exceptions, while unexpected exceptions are allowed to propagate.

    Args:
        args: A namespace of parsed command line arguments.
        api: An initialized plug.API instance.
        config_file: Path to the config file.
        ext_commands: A list of active extension commands.
    """
    hook_results = {}
    dispatch_table = {
        plug.ParserCategory.REPOS: _dispatch_repos_command,
        plug.ParserCategory.ISSUES: _dispatch_issues_command,
        plug.ParserCategory.CONFIG: _dispatch_config_command,
        plug.ParserCategory.REVIEWS: _dispatch_reviews_command,
    }

    is_ext_command = "_extension_command" in args
    if is_ext_command:
        ext_cmd = args._extension_command
        res = ext_cmd.callback(args, api)
        hook_results = {ext_cmd.name: [res]} if res else hook_results
    else:
        category = plug.ParserCategory(args.category)
        hook_results = (
            dispatch_table[category](args, config_file, api) or hook_results
        )

    if is_ext_command or args.action in [
        SETUP_PARSER,
        UPDATE_PARSER,
        CLONE_PARSER,
    ]:
        LOGGER.info(formatters.format_hook_results_output(hook_results))
    if hook_results and "hook_results_file" in args and args.hook_results_file:
        _handle_hook_results(
            hook_results=hook_results, filepath=args.hook_results_file
        )


def _dispatch_repos_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.API
) -> Optional[Mapping[str, List[plug.Result]]]:
    if args.action == SETUP_PARSER:
        return command.setup_student_repos(
            args.master_repo_urls, args.students, api
        )
    elif args.action == UPDATE_PARSER:
        command.update_student_repos(
            args.master_repo_urls, args.students, api, issue=args.issue
        )
        return None
    elif args.action == MIGRATE_PARSER:
        command.migrate_repos(args.master_repo_urls, api)
        return None
    elif args.action == CLONE_PARSER:
        return command.clone_repos(args.repos, api)
    elif args.action == CREATE_TEAMS_PARSER:
        api.ensure_teams_and_members(args.students)
        return None
    _raise_illegal_action_error(args)


def _dispatch_issues_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.API
) -> Optional[Mapping[str, List[plug.Result]]]:
    if args.action == OPEN_ISSUE_PARSER:
        command.open_issue(
            args.issue, args.master_repo_names, args.students, api
        )
        return None
    elif args.action == CLOSE_ISSUE_PARSER:
        command.close_issue(args.title_regex, args.repos, api)
        return None
    elif args.action == LIST_ISSUES_PARSER:
        return command.list_issues(
            args.repos,
            api,
            state=args.state,
            title_regex=args.title_regex or "",
            show_body=args.show_body,
            author=args.author,
        )
    _raise_illegal_action_error(args)


def _dispatch_config_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.API
) -> Optional[Mapping[str, List[plug.Result]]]:
    if args.action == VERIFY_PARSER:
        plug.manager.hook.get_api_class().verify_settings(
            args.user,
            args.org_name,
            args.base_url,
            args.token,
            args.master_org_name,
        )
        return None
    elif args.action == SHOW_CONFIG_PARSER:
        command.show_config(config_file)
        return None
    _raise_illegal_action_error(args)


def _dispatch_reviews_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.API
) -> Optional[Mapping[str, List[plug.Result]]]:
    if args.action == ASSIGN_REVIEWS_PARSER:
        command.assign_peer_reviews(
            args.master_repo_names,
            args.students,
            args.num_reviews,
            args.issue,
            api,
        )
        return None
    elif args.action == PURGE_REVIEW_TEAMS_PARSER:
        command.purge_review_teams(args.master_repo_names, args.students, api)
        return None
    elif args.action == CHECK_REVIEW_PROGRESS_PARSER:
        command.check_peer_review_progress(
            args.master_repo_names,
            args.students,
            args.title_regex,
            args.num_reviews,
            api,
        )
        return None
    _raise_illegal_action_error(args)


def _raise_illegal_action_error(args: argparse.Namespace) -> None:
    raise exception.ParseError(
        f"Unknown action {args.action} for category {args.category}"
    )


def _handle_hook_results(hook_results, filepath):
    LOGGER.warning(
        "Storing hook results to file is an alpha feature, the file format "
        "is not final"
    )
    output_file = pathlib.Path(filepath)
    util.atomic_write(plug.result_mapping_to_json(hook_results), output_file)
    LOGGER.info("Hook results stored to {}".format(filepath))
