"""Module dispatching CLI commands to RepoBee's internal.

This module essentially translates parsed and processed arguments from the
CLI into commands for RepoBee's core.

.. module:: dispatch
    :synopsis: Command dispatcher for the CLI.

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
import sys
from typing import Optional, List, Mapping, NoReturn

import repobee_plug as plug

from _repobee import command, exception, formatters, fileutil


def dispatch_command(
    args: argparse.Namespace, api: plug.PlatformAPI, config: plug.Config
) -> Mapping[str, List[plug.Result]]:
    """Handle parsed CLI arguments and dispatch commands to the appropriate
    functions. Expected exceptions are caught and turned into SystemExit
    exceptions, while unexpected exceptions are allowed to propagate.

    Args:
        args: A namespace of parsed command line arguments.
        api: An initialized plug.API instance.
        config_file: Path to the config file.
    Returns:
        A mapping of hook results.
    """
    is_extension_command = "_extension_command" in args
    hook_results = (
        _dispatch_command(args._extension_command, api)
        if is_extension_command
        else _dispatch_legacy_command(args, config, api)
    )

    _handle_hook_results(args, hook_results)

    return hook_results


def _dispatch_legacy_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
) -> Mapping[str, List[plug.Result]]:
    dispatch_table = {
        plug.cli.CoreCommand.repos: _dispatch_repos_command,
        plug.cli.CoreCommand.issues: _dispatch_issues_command,
        plug.cli.CoreCommand.config: _dispatch_config_command,
        plug.cli.CoreCommand.reviews: _dispatch_reviews_command,
        plug.cli.CoreCommand.teams: _dispatch_teams_command,
    }
    return dispatch_table[args.category](args, config, api) or {}


def _dispatch_command(
    extension_command: plug.cli.Command, api: plug.PlatformAPI
) -> Mapping[str, List[plug.Result]]:
    res = (
        extension_command.command(api=api)
        if extension_command.__requires_api__()
        else extension_command.command()
    )

    if not res:
        return {}
    elif getattr(extension_command, "_is_core_command", False):
        return res
    else:
        return {str(extension_command.__settings__.action): [res]}


def _dispatch_repos_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
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
        return command.clone_repos(
            args.repos, args.update_local, args.directory_layout, api
        )
    _raise_illegal_action_error(args)


def _dispatch_issues_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    issues = plug.cli.CoreCommand.issues
    action = args.action
    if action == issues.open:
        if args.issue:
            command.open_issue(
                args.issue, args.assignments, args.students, api
            )
        else:
            command.open_issues_from_hook_results(
                plug.json_to_result_mapping(
                    args.hook_results_file.read_text(
                        encoding=sys.getdefaultencoding()
                    )
                ),
                args.repos,
                api,
            )
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
            double_blind_key=args.double_blind_key,
        )
    _raise_illegal_action_error(args)


def _dispatch_config_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    config_category = plug.cli.CoreCommand.config
    action = args.action
    if action == config_category.verify:
        plug.manager.hook.get_api_class().verify_settings(
            args.user,
            args.org_name,
            args.base_url,
            args.token,
            args.template_org_name,
        )
        return None
    elif action == config_category.show:
        command.show_config(config, show_secrets=args.secrets)
        return None
    _raise_illegal_action_error(args)


def _dispatch_reviews_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    reviews = plug.cli.CoreCommand.reviews
    action = args.action
    if action == reviews.assign:
        command.assign_peer_reviews(
            args.assignments,
            args.students,
            args.num_reviews,
            args.issue,
            args.double_blind_key,
            api,
        )
        return None
    elif action == reviews.end:
        if plug._featflags.is_feature_enabled(
            plug._featflags.FeatureFlag.REPOBEE_4_REVIEW_COMMANDS
        ):
            command.peer.end_reviews_repobee_4(args.allocations_file, api)
        else:
            command.end_reviews(
                args.assignments, args.students, args.double_blind_key, api
            )
        return None
    elif action == reviews.check:
        if plug._featflags.is_feature_enabled(
            plug._featflags.FeatureFlag.REPOBEE_4_REVIEW_COMMANDS
        ):
            command.peer.check_reviews_repobee_4(
                args.allocations_file, args.title_regex, api
            )
        else:
            command.check_peer_review_progress(
                args.assignments,
                args.students,
                args.title_regex,
                args.num_reviews,
                args.double_blind_key,
                api,
            )
        return None
    _raise_illegal_action_error(args)


def _dispatch_teams_command(
    args: argparse.Namespace, config: plug.Config, api: plug.PlatformAPI
) -> Optional[Mapping[str, List[plug.Result]]]:
    teams = plug.cli.CoreCommand.teams
    action = args.action
    if action == teams.create:
        # list() is required here as the generator must be exhausted for teams
        # to be created
        list(
            plug.cli.io.progress_bar(
                command.create_teams(
                    args.students, plug.TeamPermission.PUSH, api
                ),
                desc="Creating teams",
                unit="teams",
                total=len(args.students),
            )
        )
        return None
    _raise_illegal_action_error(args)


def _raise_illegal_action_error(args: argparse.Namespace) -> NoReturn:
    raise exception.ParseError(
        f"Unknown action {args.action} for category {args.category}"
    )


def _handle_hook_results(
    args: argparse.Namespace, hook_results: Mapping
) -> None:
    if _should_echo_hook_results(args, hook_results):
        plug.echo(formatters.format_hook_results_output(hook_results))

    if hook_results and "hook_results_file" in args and args.hook_results_file:
        _write_hook_results(
            hook_results=hook_results, filepath=args.hook_results_file
        )


def _should_echo_hook_results(
    args: argparse.Namespace, hook_results: Mapping
) -> bool:
    is_extension_command = "_extension_command" in args

    is_applicable_action = args.action in {
        plug.cli.CoreCommand.repos.setup,
        plug.cli.CoreCommand.repos.update,
        plug.cli.CoreCommand.repos.clone,
    }

    hook_results_have_non_empty_values = bool(
        hook_results and any(hook_results.values())
    )

    return (
        is_extension_command or is_applicable_action
    ) and hook_results_have_non_empty_values


def _write_hook_results(hook_results, filepath):
    plug.log.warning(
        "Storing hook results to file is an alpha feature, the file format "
        "is not final"
    )
    output_file = pathlib.Path(filepath)
    fileutil.atomic_write(
        plug.result_mapping_to_json(hook_results), output_file
    )
    plug.echo(f"Hook results stored to {filepath}")
