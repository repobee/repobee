"""Module dispatching CLI commands to RepoBee's internal.

This module essentially translates parsed and processed arguments from the
CLI into commands for RepoBee's core.

.. module:: dispatch
    :synopsis: Command dispatcher for the CLI.

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
from typing import Optional, List

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
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
):
    """Handle parsed CLI arguments and dispatch commands to the appropriate
    functions. Expected exceptions are caught and turned into SystemExit
    exceptions, while unexpected exceptions are allowed to propagate.

    Args:
        args: A namespace of parsed command line arguments.
        api: An initialized plug.API instance.
        ext_commands: A list of active extension commands.
    """
    hook_results = {}

    ext_command_names = [cmd.name for cmd in ext_commands or []]
    is_ext_command = args.subparser in ext_command_names
    if is_ext_command:
        ext_cmd = ext_commands[ext_command_names.index(args.subparser)]
        res = ext_cmd.callback(args, api)
        hook_results = res if res else hook_results
    elif args.subparser == SETUP_PARSER:
        hook_results = command.setup_student_repos(
            args.master_repo_urls, args.students, api
        )
    elif args.subparser == UPDATE_PARSER:
        command.update_student_repos(
            args.master_repo_urls, args.students, api, issue=args.issue
        )
    elif args.subparser == OPEN_ISSUE_PARSER:
        command.open_issue(
            args.issue, args.master_repo_names, args.students, api
        )
    elif args.subparser == CLOSE_ISSUE_PARSER:
        command.close_issue(
            args.title_regex, args.master_repo_names, args.students, api
        )
    elif args.subparser == MIGRATE_PARSER:
        command.migrate_repos(args.master_repo_urls, api)
    elif args.subparser == CLONE_PARSER:
        hook_results = command.clone_repos(args.repos, api)
    elif args.subparser == VERIFY_PARSER:
        plug.manager.hook.get_api_class().verify_settings(
            args.user,
            args.org_name,
            args.base_url,
            args.token,
            args.master_org_name,
        )
    elif args.subparser == LIST_ISSUES_PARSER:
        hook_results = command.list_issues(
            args.repos,
            api,
            state=args.state,
            title_regex=args.title_regex or "",
            show_body=args.show_body,
            author=args.author,
        )
    elif args.subparser == ASSIGN_REVIEWS_PARSER:
        command.assign_peer_reviews(
            args.master_repo_names,
            args.students,
            args.num_reviews,
            args.issue,
            api,
        )
    elif args.subparser == PURGE_REVIEW_TEAMS_PARSER:
        command.purge_review_teams(args.master_repo_names, args.students, api)
    elif args.subparser == SHOW_CONFIG_PARSER:
        command.show_config()
    elif args.subparser == CHECK_REVIEW_PROGRESS_PARSER:
        command.check_peer_review_progress(
            args.master_repo_names,
            args.students,
            args.title_regex,
            args.num_reviews,
            api,
        )
    elif args.subparser == CREATE_TEAMS_PARSER:
        api.ensure_teams_and_members(args.students)
    else:
        raise exception.ParseError(
            "Illegal value for subparser: {}. "
            "This is a bug, please open an issue.".format(args.subparser)
        )

    if (
        args.subparser in [SETUP_PARSER, UPDATE_PARSER, CLONE_PARSER]
        or is_ext_command
    ):
        LOGGER.info(formatters.format_hook_results_output(hook_results))
    if hook_results and "hook_results_file" in args and args.hook_results_file:
        _handle_hook_results(
            hook_results=hook_results, filepath=args.hook_results_file
        )


def _handle_hook_results(hook_results, filepath):
    LOGGER.warning(
        "Storing hook results to file is an alpha feature, the file format "
        "is not final"
    )
    output_file = pathlib.Path(filepath)
    util.atomic_write(plug.result_mapping_to_json(hook_results), output_file)
    LOGGER.info("Hook results stored to {}".format(filepath))
