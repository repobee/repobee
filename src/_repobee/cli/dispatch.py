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


def dispatch_command(
    args: argparse.Namespace, api: plug.PlatformAPI, config_file: pathlib.Path
) -> Mapping[str, List[plug.Result]]:
    """Handle parsed CLI arguments and dispatch commands to the appropriate
    functions. Expected exceptions are caught and turned into SystemExit
    exceptions, while unexpected exceptions are allowed to propagate.

    Args:
        args: A namespace of parsed command line arguments.
        api: An initialized plug.API instance.
        config_file: Path to the config file.
    """
    hook_results = {}
    dispatch_table = {
        plug.cli.CoreCommand.repos: _dispatch_repos_command,
        plug.cli.CoreCommand.issues: _dispatch_issues_command,
        plug.cli.CoreCommand.config: _dispatch_config_command,
        plug.cli.CoreCommand.reviews: _dispatch_reviews_command,
        plug.cli.CoreCommand.teams: _dispatch_teams_command,
    }

    is_ext_command = "_extension_command" in args
    if is_ext_command:
        ext_cmd = args._extension_command
        res = (
            ext_cmd.command(api=api)
            if ext_cmd.__requires_api__()
            else ext_cmd.command()
        )
        hook_results = (
            {str(ext_cmd.__settings__.action): [res]} if res else hook_results
        )
    else:
        category = args.category
        hook_results = (
            dispatch_table[category](args, config_file, api) or hook_results
        )

    if is_ext_command or args.action in [
        plug.cli.CoreCommand.repos.setup,
        plug.cli.CoreCommand.repos.update,
        plug.cli.CoreCommand.repos.clone,
    ]:
        plug.echo(formatters.format_hook_results_output(hook_results))
    if hook_results and "hook_results_file" in args and args.hook_results_file:
        _handle_hook_results(
            hook_results=hook_results, filepath=args.hook_results_file
        )

    return hook_results


def _dispatch_repos_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    repos = plug.cli.CoreCommand.repos
    action = args.action
    if action == repos.setup:
        return command.setup_student_repos(
            args.template_repo_urls, args.students, api
        )
    elif action == repos.update:
        command.update_student_repos(
            args.template_repo_urls, args.students, api, issue=args.issue
        )
        return None
    elif action == repos.migrate:
        command.migrate_repos(args.template_repo_urls, api)
        return None
    elif action == repos.clone:
        return command.clone_repos(args.repos, api)
    _raise_illegal_action_error(args)


def _dispatch_issues_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    issues = plug.cli.CoreCommand.issues
    action = args.action
    if action == issues.open:
        command.open_issue(args.issue, args.assignments, args.students, api)
        return None
    elif action == issues.close:
        command.close_issue(args.title_regex, args.repos, api)
        return None
    elif action == issues.list:
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
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    config = plug.cli.CoreCommand.config
    action = args.action
    if action == config.verify:
        plug.manager.hook.get_api_class().verify_settings(
            args.user,
            args.org_name,
            args.base_url,
            args.token,
            args.template_org_name,
        )
        return None
    elif action == config.show:
        command.show_config(config_file)
        return None
    _raise_illegal_action_error(args)


def _dispatch_reviews_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    reviews = plug.cli.CoreCommand.reviews
    action = args.action
    if action == reviews.assign:
        command.assign_peer_reviews(
            args.assignments, args.students, args.num_reviews, args.issue, api,
        )
        return None
    elif action == reviews.end:
        command.purge_review_teams(args.assignments, args.students, api)
        return None
    elif action == reviews.check:
        command.check_peer_review_progress(
            args.assignments,
            args.students,
            args.title_regex,
            args.num_reviews,
            api,
        )
        return None
    _raise_illegal_action_error(args)


def _dispatch_teams_command(
    args: argparse.Namespace, config_file: pathlib.Path, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    teams = plug.cli.CoreCommand.teams
    action = args.action
    if action == teams.create:
        command.create_teams(args.students, plug.TeamPermission.PUSH, api)
        return None
    _raise_illegal_action_error(args)


def _raise_illegal_action_error(args: argparse.Namespace) -> None:
    raise exception.ParseError(
        f"Unknown action {args.action} for category {args.category}"
    )


def _handle_hook_results(hook_results, filepath):
    plug.log.warning(
        "Storing hook results to file is an alpha feature, the file format "
        "is not final"
    )
    output_file = pathlib.Path(filepath)
    util.atomic_write(plug.result_mapping_to_json(hook_results), output_file)
    plug.echo("Hook results stored to {}".format(filepath))
