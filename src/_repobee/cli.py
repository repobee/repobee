"""CLI module.

This module contains the CLI for _repobee.

.. module:: cli
    :synopsis: The CLI for _repobee.

.. moduleauthor:: Simon Larsén
"""

import types
import argparse
import pathlib
import os
import sys
import re
from contextlib import contextmanager
from typing import List, Iterable, Optional, Tuple

import logging
import daiquiri

import repobee_plug as plug

import _repobee
from _repobee import plugin
from _repobee import tuples
from _repobee import command
from _repobee import util
from _repobee import exception
from _repobee import config
from _repobee import constants

daiquiri.setup(
    level=logging.INFO,
    outputs=(
        daiquiri.output.Stream(
            sys.stdout,
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="%(color)s[%(levelname)s] %(message)s%(color_stop)s"
            ),
        ),
        daiquiri.output.File(
            filename="{}.log".format(_repobee._external_package_name),
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="%(asctime)s [PID %(process)d] [%(levelname)s] "
                "%(name)s -> %(message)s"
            ),
        ),
    ),
)


def _filter_tokens():
    """Filter out any secure tokens from log output."""
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        # from URLS (e.g. git error messages)
        record.msg = re.sub("https://.*?@", "https://", record.msg)
        # from show-config output
        record.msg = re.sub(r"token\s*=\s*.*", "token = xxxxxxxxx", record.msg)
        return record

    logging.setLogRecordFactory(record_factory)


_filter_tokens()

LOGGER = daiquiri.getLogger(__file__)
SUB = "subparser"

# Any new subparser mus tbe added to the PARSER_NAMES tuple!
SETUP_PARSER = "setup"
UPDATE_PARSER = "update"
CLONE_PARSER = "clone"
MIGRATE_PARSER = "migrate"
OPEN_ISSUE_PARSER = "open-issues"
CLOSE_ISSUE_PARSER = "close-issues"
LIST_ISSUES_PARSER = "list-issues"
VERIFY_PARSER = "verify-settings"
ASSIGN_REVIEWS_PARSER = "assign-reviews"
PURGE_REVIEW_TEAMS_PARSER = "end-reviews"
CHECK_REVIEW_PROGRESS_PARSER = "check-reviews"
SHOW_CONFIG_PARSER = "show-config"

PARSER_NAMES = (
    SETUP_PARSER,
    UPDATE_PARSER,
    CLONE_PARSER,
    MIGRATE_PARSER,
    OPEN_ISSUE_PARSER,
    CLOSE_ISSUE_PARSER,
    LIST_ISSUES_PARSER,
    VERIFY_PARSER,
    ASSIGN_REVIEWS_PARSER,
    PURGE_REVIEW_TEAMS_PARSER,
    SHOW_CONFIG_PARSER,
    CHECK_REVIEW_PROGRESS_PARSER,
)


# add any diprecated parsers to this dict on the following form:
#
# ASSIGN_REVIEWS_PARSER_OLD: tuples.Deprecation(
#     replacement=ASSIGN_REVIEWS_PARSER, remove_by="v2.0.0"
# ),
DEPRECATED_PARSERS = {
    "purge-review-teams": tuples.Deprecation(
        replacement=PURGE_REVIEW_TEAMS_PARSER, remove_by="v2.2.0"
    )
}

# any pre-parser options go here
PRE_PARSER_PLUG_OPTS = ["-p", "--plug"]
PRE_PARSER_NO_PLUGS = "--no-plugins"
PRE_PARSER_SHOW_ALL_OPTS = "--show-all-opts"

# this list should include all pre-parser flags
PRE_PARSER_FLAGS = [PRE_PARSER_NO_PLUGS, PRE_PARSER_SHOW_ALL_OPTS]


def parse_args(
    sys_args: Iterable[str],
    show_all_opts: bool = False,
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
) -> Tuple[None, Optional[plug.API]]:
    """Parse the command line arguments and initialize an API.

    Args:
        sys_args: A list of command line arguments.
        show_all_opts: If False, CLI arguments that are configure in the
            configuration file are not shown in help menus.
        ext_commands: A list of extension commands.

    Returns:
        a argparse.Namespace namedtuple with the arguments, and an initialized
        plug.API instance (or None of testing connection).
    """
    parser = _create_parser(show_all_opts, ext_commands)
    args = parser.parse_args(_handle_deprecation(sys_args))
    ext_command_names = [cmd.name for cmd in ext_commands or []]
    subparser = getattr(args, SUB)

    if subparser == SHOW_CONFIG_PARSER:
        return argparse.Namespace(**vars(args)), None
    elif ext_commands and subparser in ext_command_names:
        return _handle_extension_parsing(
            ext_commands[ext_command_names.index(subparser)], args
        )

    _validate_tls_url(args.base_url)
    token = _parse_token(args)

    if subparser == VERIFY_PARSER:
        # quick parse for verify connection
        return (
            argparse.Namespace(
                subparser=VERIFY_PARSER,
                org_name=args.org_name,
                base_url=args.base_url,
                user=args.user,
                traceback=args.traceback,
                master_org_name=args.master_org_name
                if "master_org_name" in args
                else None,
                token=token,
            ),
            None,
        )
    elif subparser == CLONE_PARSER:
        # only if clone is chosen should plugins be able to hook in
        plug.manager.hook.parse_args(args=args)

    api = _connect_to_api(
        args.base_url,
        token,
        args.org_name,
        args.user if "user" in args else None,
    )

    master_org_name = args.org_name
    if "master_org_name" in args and args.master_org_name is not None:
        master_org_name = args.master_org_name
    master_names = args.master_repo_names
    master_urls = _repo_names_to_urls(master_names, master_org_name, api)
    assert master_urls and master_names

    args_dict = vars(args)
    args_dict.setdefault("master_org_name", None)
    args_dict.setdefault("title_regex", None)
    args_dict.setdefault("state", None)
    args_dict.setdefault("show_body", None)
    args_dict.setdefault("author", None)
    args_dict.setdefault("num_reviews", None)
    args_dict["students"] = _extract_groups(args)
    args_dict["issue"] = (
        util.read_issue(args.issue) if "issue" in args and args.issue else None
    )
    args_dict["master_repo_urls"] = master_urls
    args_dict["master_repo_names"] = master_names
    args_dict["token"] = token

    return argparse.Namespace(**args_dict), api


def _parse_token(args):
    """Get the OUATH2 token from the args or an environment variable."""
    # environment token overrides config
    return os.getenv("REPOBEE_OAUTH") or (
        args.token if "token" in args else ""
    )


def _handle_extension_parsing(ext_command, args):
    """Handle parsing of extension command arguments."""
    api = None
    if ext_command.requires_api:
        token = _parse_token(args)
        args.token = token
        api = _connect_to_api(args.base_url, token, args.org_name, args.user)
    return args, api


def _validate_tls_url(url):
    """Url must use the https protocol."""
    if not url.startswith("https://"):
        raise exception.ParseError(
            "unsupported protocol in {}: "
            "for security reasons, only https is supported".format(url)
        )


def _handle_deprecation(sys_args: List[str]) -> List[str]:
    """If the first argument on the arglist is a deprecated command, replace it
    with the corresponding current command and issue a warning.

    Returns:
        The sys_args list with any deprecated command replaced with the current
        one.
    """
    if not sys_args:
        return []

    parser_name = sys_args[0]
    if parser_name in DEPRECATED_PARSERS:
        deprecation = DEPRECATED_PARSERS[parser_name]
        LOGGER.warning(
            "Use of '{}' has been deprecated and will be removed by {}, "
            "use '{}' instead".format(
                parser_name, deprecation.remove_by, deprecation.replacement
            )
        )
        return [deprecation.replacement] + sys_args[1:]

    return list(sys_args)


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
    ext_command_names = [cmd.name for cmd in ext_commands or []]
    if ext_command_names and args.subparser in ext_command_names:
        ext_cmd = ext_commands[ext_command_names.index(args.subparser)]
        with _sys_exit_on_expected_error():
            ext_cmd.callback(args, api)
    elif args.subparser == SETUP_PARSER:
        with _sys_exit_on_expected_error():
            command.setup_student_repos(
                args.master_repo_urls, args.students, api
            )
    elif args.subparser == UPDATE_PARSER:
        with _sys_exit_on_expected_error():
            command.update_student_repos(
                args.master_repo_urls, args.students, api, issue=args.issue
            )
    elif args.subparser == OPEN_ISSUE_PARSER:
        with _sys_exit_on_expected_error():
            command.open_issue(
                args.issue, args.master_repo_names, args.students, api
            )
    elif args.subparser == CLOSE_ISSUE_PARSER:
        with _sys_exit_on_expected_error():
            command.close_issue(
                args.title_regex, args.master_repo_names, args.students, api
            )
    elif args.subparser == MIGRATE_PARSER:
        with _sys_exit_on_expected_error():
            command.migrate_repos(args.master_repo_urls, api)
    elif args.subparser == CLONE_PARSER:
        with _sys_exit_on_expected_error():
            command.clone_repos(args.master_repo_names, args.students, api)
    elif args.subparser == VERIFY_PARSER:
        with _sys_exit_on_expected_error():
            plug.manager.hook.get_api_class().verify_settings(
                args.user,
                args.org_name,
                args.base_url,
                args.token,
                args.master_org_name,
            )
    elif args.subparser == LIST_ISSUES_PARSER:
        with _sys_exit_on_expected_error():
            command.list_issues(
                args.master_repo_names,
                args.students,
                api,
                state=args.state,
                title_regex=args.title_regex or "",
                show_body=args.show_body,
                author=args.author,
            )
    elif args.subparser == ASSIGN_REVIEWS_PARSER:
        with _sys_exit_on_expected_error():
            command.assign_peer_reviews(
                args.master_repo_names,
                args.students,
                args.num_reviews,
                args.issue,
                api,
            )
    elif args.subparser == PURGE_REVIEW_TEAMS_PARSER:
        with _sys_exit_on_expected_error():
            command.purge_review_teams(
                args.master_repo_names, args.students, api
            )
    elif args.subparser == SHOW_CONFIG_PARSER:
        with _sys_exit_on_expected_error():
            command.show_config()
    elif args.subparser == CHECK_REVIEW_PROGRESS_PARSER:
        with _sys_exit_on_expected_error():
            command.check_peer_review_progress(
                args.master_repo_names,
                args.students,
                args.title_regex,
                args.num_reviews,
                api,
            )
    else:
        raise exception.ParseError(
            "Illegal value for subparser: {}. "
            "This is a bug, please open an issue.".format(args.subparser)
        )


def _add_peer_review_parsers(base_parsers, subparsers):
    assign_parser = subparsers.add_parser(
        ASSIGN_REVIEWS_PARSER,
        description=(
            "For each student repo, create a review team with read access "
            "named <student-repo-name>-review and randomly assign "
            "other students to it. All students are assigned to the same "
            "amount of review teams, as specified by `--num-reviews`. Note "
            "that `--num-reviews` must be strictly less than the amount of "
            "students. Note that review allocation strategy may be altered "
            "by plugins."
        ),
        help="Assign students to peer review each others' repos.",
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )
    assign_parser.add_argument(
        "-n",
        "--num-reviews",
        metavar="N",
        help="Assign each student to review n repos (consequently, each repo "
        "is reviewed by n students). n must be strictly smaller than the "
        "amount of students.",
        type=int,
        default=1,
    )
    assign_parser.add_argument(
        "-i",
        "--issue",
        help=(
            "Path to an issue to open in student repos. If specified, this "
            "issue will be opened in each student repo, and the body will be "
            "prepended with user mentions of all students assigned to review "
            "the repo. NOTE: The first line is assumed to be the title."
        ),
        type=str,
    )
    check_review_progress = subparsers.add_parser(
        CHECK_REVIEW_PROGRESS_PARSER,
        description=(
            "Check which students have opened review review issues in their "
            "assigned repos. As it is possible for students to leave the peer "
            "review teams on their own, the command checks that each student "
            "is assigned to the expected amound of teams. There is currently "
            "no way to check if students have been swapped around, so using "
            "this command fow grading purposes is not recommended."
        ),
        help="Check which students have opened peer review issues.",
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )
    check_review_progress.add_argument(
        "-r",
        "--title-regex",
        help=(
            "Regex to match against titles. Only issues matching this regex "
            "will count as review issues."
        ),
        required=True,
    )
    check_review_progress.add_argument(
        "-n",
        "--num-reviews",
        metavar="N",
        help=(
            "The expected amount of reviews each student should be assigned "
            "to perform. If a student is not assigned to `num_reviews` "
            "review teams, warnings will be displayed."
        ),
        type=int,
        required=True,
    )
    subparsers.add_parser(
        PURGE_REVIEW_TEAMS_PARSER,
        description=(
            "Delete review allocations assigned with `assign-reviews`. "
            "This is a destructive action, as the allocations for reviews "
            "are irreversibly deleted. The purpose of this command is to "
            "revoke the reviewers' read access to reviewed repos, and to "
            "clean up the allocations (i.e. deleting the review teams when "
            "using GitHub, or groups when using GitLab). It will however not "
            "do anything with the review issues. You can NOT run "
            "`check-reviews` after `end-reviews`, as the former "
            "needs the allocations to function properly. Use this command "
            "only when reviews are done."
        ),
        help=(
            "Delete review allocations created by `assign-reviews`. "
            "DESTRUCTIVE ACTION: read help section before using."
        ),
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )


def _add_issue_parsers(base_parsers, subparsers):
    open_parser = subparsers.add_parser(
        OPEN_ISSUE_PARSER,
        description=(
            "Open issues in student repositories. For each master repository "
            "specified, the student list is traversed. For every student repo "
            "found, the issue specified by the `--issue` option is opened. "
            "NOTE: The first line of the issue file is assumed to be the "
            "issue title!"
        ),
        help="Open issues in student repos.",
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )
    open_parser.add_argument(
        "-i",
        "--issue",
        help="Path to an issue. The first line is assumed to be the title.",
        type=str,
        required=True,
    )

    close_parser = subparsers.add_parser(
        CLOSE_ISSUE_PARSER,
        description=(
            "Close issues in student repos based on a regex. For each master "
            "repository specified, the student list is traversed. For every "
            "student repo found, any open issues matching the `--title-regex` "
            "are closed."
        ),
        help="Close issues in student repos.",
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )
    close_parser.add_argument(
        "-r",
        "--title-regex",
        help=(
            "Regex to match titles against. Any issue whose title matches the "
            "regex will be closed."
        ),
        type=str,
        required=True,
    )

    list_parser = subparsers.add_parser(
        LIST_ISSUES_PARSER,
        description="List issues in student repos.",
        help="List issues in student repos.",
        parents=base_parsers,
        formatter_class=_OrderedFormatter,
    )
    list_parser.add_argument(
        "-r",
        "--title-regex",
        help=(
            "Regex to match against titles. Only issues matching this regex "
            "will be listed."
        ),
    )
    list_parser.add_argument(
        "-b",
        "--show-body",
        action="store_true",
        help="Show the body of the issue, alongside the default info.",
    )
    list_parser.add_argument(
        "-a",
        "--author",
        help="Only show issues by this author.",
        type=str,
        default=None,
    )
    state = list_parser.add_mutually_exclusive_group()
    state.add_argument(
        "--open",
        help="List open issues (default).",
        action="store_const",
        dest="state",
        const=plug.IssueState.OPEN,
    )
    state.add_argument(
        "--closed",
        help="List closed issues.",
        action="store_const",
        dest="state",
        const=plug.IssueState.CLOSED,
    )
    state.add_argument(
        "--all",
        help="List all issues (open and closed).",
        action="store_const",
        dest="state",
        const=plug.IssueState.ALL,
    )
    list_parser.set_defaults(state=plug.IssueState.OPEN)


class _OrderedFormatter(argparse.HelpFormatter):
    """A formatter class for putting out the help section in a proper order.
    All of the arguments that are configurable in the configuration file
    should appear at the bottom (in arbitrary, but always the same, order).
    Any other arguments should appear in the order they are added.

    The internals of the formatter classes are technically not public,
    so this class is "unsafe" when it comes to new versions of Python. It may
    have to be disabled for future versions, but it works for 3.5, 3.6 and 3.7
    at the time of writing. If this turns troublesome, it may be time to
    switch to some other CLI library.
    """

    def add_arguments(self, actions):
        """Order actions by the name  of the long argument, and then add them
        as arguments.

        The order is the following:

        [ NON-CONFIGURABLE | CONFIGURABLE | DEBUG ]

        Non-configurable arguments added without modification, which by
        default is the order they are added to the parser. Configurable
        arguments are added in the order defined by
        :py:const:`constants.ORDERED_CONFIGURABLE_ARGS`. Finally, debug
        commands (such as ``--traceback``) are added in arbitrary (but
        consistent) order.
        """
        args_order = tuple(
            "--" + name.replace("_", "-")
            for name in constants.ORDERED_CONFIGURABLE_ARGS
        ) + ("--traceback",)

        def key(action):
            if len(action.option_strings) < 2:
                return -1
            long_arg = action.option_strings[1]
            if long_arg in args_order:
                return args_order.index(long_arg)
            return -1

        actions = sorted(actions, key=key)
        super().add_arguments(actions)


def create_parser_for_docs():
    """Create a parser showing all options for the default CLI
    documentation.
    """
    daiquiri.setup(level=logging.FATAL)
    # load default plugins
    plugin.initialize_plugins([_repobee.constants.DEFAULT_PLUGIN])
    ext_commands = plug.manager.hook.create_extension_command()
    return _create_parser(show_all_opts=True, ext_commands=ext_commands)


def _create_parser(show_all_opts, ext_commands):
    """Create the parser."""
    loaded_plugins = ", ".join(
        [
            p.__name__.split(".")[-1]
            for p in plug.manager.get_plugins()
            if isinstance(p, types.ModuleType)
        ]
    )

    program_description = (
        "A CLI tool for administrating large amounts of git repositories "
        "on GitHub and\nGitLab instances. Read the docs at: "
        "https://repobee.readthedocs.io\n\n"
    )

    if not show_all_opts and config.get_configured_defaults():
        program_description += (
            "CLI options that are set in the config file are suppressed in "
            "help sections,\nrun with pre-parser option {all_opts_arg} to "
            "unsuppress.\nExample: repobee {all_opts_arg} setup -h\n\n".format(
                all_opts_arg=PRE_PARSER_SHOW_ALL_OPTS
            )
        )
    program_description += "Loaded plugins: " + loaded_plugins

    parser = argparse.ArgumentParser(
        prog="repobee",
        description=program_description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Display version info",
        action="version",
        version="{} v{}".format(
            _repobee._external_package_name, _repobee.__version__
        ),
    )
    _add_subparsers(parser, show_all_opts, ext_commands)

    return parser


def _add_extension_parsers(subparsers, ext_commands, base_parser):
    """Add extension parsers defined by plugins."""
    if not ext_commands:
        return []
    for cmd in ext_commands:
        parents = (
            [base_parser, cmd.parser] if cmd.requires_api else [cmd.parser]
        )
        ext_parser = subparsers.add_parser(
            cmd.name,
            help=cmd.help,
            description=cmd.description,
            parents=parents,
            formatter_class=_OrderedFormatter,
        )
        if not cmd.requires_api:
            _add_traceback_arg(ext_parser)

    return ext_commands


def _add_subparsers(parser, show_all_opts, ext_commands):
    """Add all of the subparsers to the parser. Note that the parsers prefixed
    with `base_` do not have any parent parsers, so any parser inheriting from
    them must also inherit from the required `base_parser` (unless it is a
    `base_` prefixed parser, of course).
    """

    base_parser, base_student_parser, master_org_parser = _create_base_parsers(
        show_all_opts
    )

    repo_name_parser = argparse.ArgumentParser(add_help=False)
    repo_name_parser.add_argument(
        "--mn",
        "--master-repo-names",
        help="One or more names of master repositories. Names must either "
        "refer to local directories, or to master repositories in the "
        "target organization.",
        type=str,
        required=True,
        nargs="+",
        dest="master_repo_names",
    )

    subparsers = parser.add_subparsers(dest=SUB)
    subparsers.required = True

    subparsers.add_parser(
        SETUP_PARSER,
        help="Setup student repos.",
        description=(
            "Setup student repositories based on master repositories. "
            "This command performs three primary actions: sets up the "
            "student teams, creates one student repository for each "
            "master repository and finally pushes the master repo files to "
            "the corresponding student repos. It is perfectly safe to run "
            "this command several times, as any previously performed step "
            "will simply be skipped."
        ),
        parents=[
            base_parser,
            base_student_parser,
            master_org_parser,
            repo_name_parser,
        ],
        formatter_class=_OrderedFormatter,
    )

    update = subparsers.add_parser(
        UPDATE_PARSER,
        help="Update existing student repos.",
        description=(
            "Push changes from master repos to student repos. If the "
            "`--issue` option is provided, the specified issue is opened in "
            "any repo to which pushes fail (because the students have pushed "
            "something already)."
        ),
        parents=[
            base_parser,
            base_student_parser,
            master_org_parser,
            repo_name_parser,
        ],
        formatter_class=_OrderedFormatter,
    )
    update.add_argument(
        "-i",
        "--issue",
        help=(
            "Path to issue to open in repos to which pushes fail. "
            "Assumes that the first line is the title of the issue."
        ),
        type=str,
    )

    clone = subparsers.add_parser(
        CLONE_PARSER,
        help="Clone student repos.",
        description="Clone student repos asynchronously in bulk.",
        parents=[base_parser, base_student_parser, repo_name_parser],
        formatter_class=_OrderedFormatter,
    )

    plug.manager.hook.clone_parser_hook(clone_parser=clone)

    subparsers.add_parser(
        MIGRATE_PARSER,
        help="Migrate repositories into the target organization.",
        description=(
            "Migrate repositories into the target organization. "
            "The repos must be local on disk to be migrated. Note that "
            "migrated repos will be private."
        ),
        parents=[repo_name_parser, base_parser],
        formatter_class=_OrderedFormatter,
    )

    _add_issue_parsers(
        [base_parser, base_student_parser, repo_name_parser], subparsers
    )
    _add_peer_review_parsers(
        [base_parser, base_student_parser, repo_name_parser], subparsers
    )

    show_config = subparsers.add_parser(
        SHOW_CONFIG_PARSER,
        help="Show the configuration file",
        description=(
            "Show the contents of the configuration file. If no configuration "
            "file can be found, show the path where repobee expectes to find "
            "it."
        ),
        formatter_class=_OrderedFormatter,
    )
    _add_traceback_arg(show_config)

    subparsers.add_parser(
        VERIFY_PARSER,
        help="Verify core settings.",
        description="Verify core settings by trying various API requests.",
        parents=[base_parser, master_org_parser],
        formatter_class=_OrderedFormatter,
    )

    return _add_extension_parsers(subparsers, ext_commands, base_parser)


def _create_base_parsers(show_all_opts):
    """Create the base parsers."""
    configured_defaults = config.get_configured_defaults()
    config.execute_config_hooks()

    def default(arg_name):
        return (
            configured_defaults[arg_name]
            if arg_name in configured_defaults
            else None
        )

    def configured(arg_name):
        return arg_name in configured_defaults

    def api_requires(arg_name):
        return arg_name in plug.manager.hook.api_init_requires()

    def hide_api_arg(arg_name):
        # note that API args that are not required should not be shown even
        # when show_all_opts is True, as they are not relevant.
        return not api_requires(arg_name) or (
            not show_all_opts and configured(arg_name)
        )

    def hide_configurable_arg(arg_name):
        return not show_all_opts and configured(arg_name)

    # API args help sections
    user_help = argparse.SUPPRESS if hide_api_arg("user") else "Your username."
    org_name_help = (
        argparse.SUPPRESS
        if hide_api_arg("org_name")
        else "Name of the target organization"
    )
    base_url_help = (
        argparse.SUPPRESS
        if hide_api_arg("base_url")
        else (
            "Base url to a platform API. Must be HTTPS. For example, with "
            "github.com, the base url is https://api.github.com, and with "
            "GitHub enterprise, the url is https://<ENTERPRISE_HOST>/api/v3"
        )
    )
    token_help = (
        argparse.SUPPRESS
        if hide_api_arg("token")
        else (
            "OAUTH token for the platform instance. Can also be specified in "
            "the `REPOBEE_OAUTH` environment variable."
        )
    )

    # other configurable args help sections
    # these should not be checked against the api_requires function
    students_file_help = (
        argparse.SUPPRESS
        if hide_configurable_arg("students_file")
        else (
            "Path to a list of student usernames. Put multiple usernames on "
            "each line to form groups."
        )
    )
    master_org_help = (
        argparse.SUPPRESS
        if hide_configurable_arg("master_org_name")
        else (
            "Name of the organization containing the master repos. "
            "Defaults to the same value as `-o|--org-name` if left "
            "unspecified. Note that config values take precedence "
            "over this default."
        )
    )

    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        "-u",
        "--user",
        help=user_help,
        type=str,
        required=not configured("user") and api_requires("user"),
        default=default("user"),
    )

    base_parser.add_argument(
        "-o",
        "--org-name",
        help=org_name_help,
        type=str,
        required=not configured("org_name") and api_requires("org_name"),
        default=default("org_name"),
    )
    base_parser.add_argument(
        "--bu",
        "--base-url",
        help=base_url_help,
        type=str,
        required=not configured("base_url") and api_requires("base_url"),
        default=default("base_url"),
        dest="base_url",
    )
    base_parser.add_argument(
        "-t", "--token", help=token_help, type=str, default=default("token")
    )

    _add_traceback_arg(base_parser)
    # base parser for when student lists are involved
    base_student_parser = argparse.ArgumentParser(add_help=False)
    students = base_student_parser.add_mutually_exclusive_group(
        required=not configured("students_file")
    )
    students.add_argument(
        "--sf",
        "--students-file",
        help=students_file_help,
        type=str,
        default=default("students_file"),
        dest="students_file",
    )
    students.add_argument(
        "-s",
        "--students",
        help="One or more whitespace separated student usernames.",
        type=str,
        nargs="+",
    )

    master_org_parser = argparse.ArgumentParser(add_help=False)
    master_org_parser.add_argument(
        "--mo",
        "--master-org-name",
        help=master_org_help,
        default=default("master_org_name"),
        dest="master_org_name",
    )

    return (base_parser, base_student_parser, master_org_parser)


def _add_traceback_arg(parser):
    parser.add_argument(
        "--tb",
        "--traceback",
        help="Show the full traceback of critical exceptions.",
        action="store_true",
        dest="traceback",
    )


@contextmanager
def _sys_exit_on_expected_error():
    try:
        yield
    except exception.PushFailedError as exc:
        LOGGER.error(
            "There was an error pushing to {}. "
            "Verify that your token has adequate access.".format(exc.url)
        )
        sys.exit(1)
    except exception.CloneFailedError as exc:
        LOGGER.error(
            "There was an error cloning from {}. "
            "Does the repo really exist?".format(exc.url)
        )
        sys.exit(1)
    except exception.GitError:
        LOGGER.error("Something went wrong with git. See the logs for info.")
        sys.exit(1)
    except exception.APIError as exc:
        LOGGER.error("Exiting beacuse of {.__class__.__name__}".format(exc))
        sys.exit(1)


def _extract_groups(args: argparse.Namespace) -> List[str]:
    """Extract groups from args namespace.`

    Args:
        args: A namespace object.

    Returns:
        a list of student usernames, or None of neither `students` or
        `students_file` is in the namespace.
    """
    if "students" in args and args.students:
        students = [plug.Team(members=[s]) for s in args.students]
    elif "students_file" in args and args.students_file:
        students_file = pathlib.Path(args.students_file)
        try:  # raises FileNotFoundError in 3.5 if no such file exists
            students_file = students_file.resolve()
        except FileNotFoundError:
            pass  # handled by next check
        if not students_file.is_file():
            raise exception.FileError(
                "'{!s}' is not a file".format(students_file)
            )
        if not students_file.stat().st_size:
            raise exception.FileError("'{!s}' is empty".format(students_file))
        students = [
            plug.Team(members=[s for s in group.strip().split()])
            for group in students_file.read_text(
                encoding=sys.getdefaultencoding()
            ).split(os.linesep)
            if group  # skip blank lines
        ]
    else:
        students = None

    return students


def _connect_to_api(
    base_url: str, token: str, org_name: str, user: str
) -> plug.API:
    """Return an API instance connected to the specified API endpoint."""
    required_args = plug.manager.hook.api_init_requires()
    kwargs = {}
    if "base_url" in required_args:
        kwargs["base_url"] = base_url
    if "token" in required_args:
        kwargs["token"] = token
    if "org_name" in required_args:
        kwargs["org_name"] = org_name
    if "user" in required_args:
        kwargs["user"] = user
    api_class = plug.manager.hook.get_api_class()
    try:
        return api_class(**kwargs)
    except exception.NotFoundError:
        # more informative message
        raise exception.NotFoundError(
            "either organization {} could not be found, "
            "or the base url '{}' is incorrect".format(org_name, base_url)
        )


def _repo_names_to_urls(
    repo_names: Iterable[str], org_name: str, api: plug.API
) -> List[str]:
    """Use the repo_names to extract urls to the repos. Look for git
    repos with the correct names in the local directory and create local uris
    for them.  For the rest, create urls to the repos assuming they are in the
    target organization. Do note that there is _no_ guarantee that the remote
    repos exist as checking this takes too much time with the REST API.

    A possible improvement would be to use the GraphQL API for this function.

    Args:
        repo_names: names of repositories.
        org_name: Name of the organization these repos are expected in.
        api: An API instance.

    Returns:
        a list of urls corresponding to the repo_names.
    """
    local = [
        name for name in repo_names if util.is_git_repo(os.path.abspath(name))
    ]
    non_local = [name for name in repo_names if name not in local]

    non_local_urls = api.get_repo_urls(non_local, org_name)
    local_uris = [
        pathlib.Path(os.path.abspath(repo_name)).as_uri()
        for repo_name in local
    ]
    return non_local_urls + local_uris


def parse_preparser_options(sys_args: List[str]):
    """Parse all arguments that can somehow alter the end-user CLI, such
    as plugins.

    Args:
        sys_args: Command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="repobee", description="plugin pre-parser for _repobee."
    )

    mutex_grp = parser.add_mutually_exclusive_group()
    mutex_grp.add_argument(
        *PRE_PARSER_PLUG_OPTS,
        help="Specify the name of a plugin to use.",
        type=str,
        action="append",
        default=None
    )
    mutex_grp.add_argument(
        PRE_PARSER_NO_PLUGS, help="Disable plugins.", action="store_true"
    )
    mutex_grp.add_argument(
        PRE_PARSER_SHOW_ALL_OPTS,
        help="Unsuppress all options in help menus",
        action="store_true",
    )

    args = parser.parse_args(sys_args)

    return args
