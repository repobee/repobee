"""Definition of the primary parser for RepoBee.

.. module:: mainparser
    :synopsis: The primary parser for RepoBee.

.. moduleauthor:: Simon Larsén
"""

import types
import argparse
import pathlib

import logging
from typing import List, Optional

import daiquiri

import repobee_plug as plug

import _repobee
from _repobee import plugin
from _repobee import util
from _repobee import config
from _repobee import constants
from _repobee.cli.preparser import PRE_PARSER_SHOW_ALL_OPTS

LOGGER = daiquiri.getLogger(__file__)

SUB = "category"
ACTION = "action"

_HOOK_RESULTS_PARSER = argparse.ArgumentParser(add_help=False)
_HOOK_RESULTS_PARSER.add_argument(
    "--hook-results-file",
    help="Path to a file to store results from plugin hooks in. The "
    "results are stored as JSON, regardless of file extension.",
    type=str,
    default=None,
)
_REPO_NAME_PARSER = argparse.ArgumentParser(add_help=False)
_REPO_NAME_PARSER.add_argument(
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
_REPO_DISCOVERY_PARSER = argparse.ArgumentParser(add_help=False)
_DISCOVERY_MUTEX_GRP = _REPO_DISCOVERY_PARSER.add_mutually_exclusive_group(
    required=True
)
_DISCOVERY_MUTEX_GRP.add_argument(
    "--mn",
    "--master-repo-names",
    help="One or more names of master repositories. Names must either "
    "refer to local directories, or to master repositories in the "
    "target organization.",
    type=str,
    nargs="+",
    dest="master_repo_names",
)
_DISCOVERY_MUTEX_GRP.add_argument(
    "--discover-repos",
    help="Discover all repositories for the specified students. NOTE: This "
    "is expensive in terms of API requests, if you have a rate limit you "
    "may want to avoid this option.",
    action="store_true",
)


def create_parser_for_docs() -> argparse.ArgumentParser:
    """Create a parser showing all options for the default CLI
    documentation.

    Returns:
        The primary parser, specifically for generating documentation.
    """
    daiquiri.setup(level=logging.FATAL)
    # load default plugins
    plugin.initialize_default_plugins()
    ext_commands = plug.manager.hook.create_extension_command()
    return create_parser(
        show_all_opts=True,
        ext_commands=ext_commands,
        config_file=_repobee.constants.DEFAULT_CONFIG_FILE,
    )


def create_parser(
    show_all_opts: bool,
    ext_commands: Optional[List[plug.ExtensionCommand]],
    config_file: pathlib.Path,
) -> argparse.ArgumentParser:
    """Create the primary parser.

    Args:
        show_all_opts: If False, help sections for options with configured
            defaults are suppressed. Otherwise, all options are shown.
        ext_commands: A list of extension commands.
        config_file: Path to the config file.
    Returns:
        The primary parser.
    """

    def _versioned_plugin_name(plugin_module: types.ModuleType) -> str:
        """Return the name of the plugin, with version if available."""
        name = plugin_module.__name__.split(".")[-1]
        ver = plugin.resolve_plugin_version(plugin_module)
        return "{}-{}".format(name, ver) if ver else name

    loaded_plugins = ", ".join(
        [
            _versioned_plugin_name(p)
            for p in plug.manager.get_plugins()
            if isinstance(p, types.ModuleType)
            and not plugin.is_default_plugin(p)
        ]
    )

    program_description = (
        "A CLI tool for administrating large amounts of git repositories "
        "on GitHub and\nGitLab instances. Read the docs at: "
        "https://repobee.readthedocs.io\n\n"
    )

    if not show_all_opts and constants.DEFAULT_CONFIG_FILE.is_file():
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
        version="{}".format(_repobee.__version__),
    )
    _add_subparsers(parser, show_all_opts, ext_commands, config_file)

    return parser


def _add_subparsers(parser, show_all_opts, ext_commands, config_file):
    """Add all of the subparsers to the parser. Note that the parsers prefixed
    with `base_` do not have any parent parsers, so any parser inheriting from
    them must also inherit from the required `base_parser` (unless it is a
    `base_` prefixed parser, of course).
    """

    base_parser, base_student_parser, master_org_parser = _create_base_parsers(
        show_all_opts, config_file
    )

    subparsers = parser.add_subparsers(dest=SUB)
    subparsers.required = True
    categories = {}

    def _create_category_parsers(category, help, description):
        category_command = subparsers.add_parser(
            category.name, help=help, description=description
        )
        category_parsers = category_command.add_subparsers(dest=ACTION)
        category_parsers.required = True
        categories[category] = category_parsers
        return category_parsers

    repo_parsers = _create_category_parsers(
        plug.CoreCommand.repos,
        description="Manage repositories.",
        help="Manage repositories.",
    )
    issues_parsers = _create_category_parsers(
        plug.CoreCommand.issues,
        description="Manage issues.",
        help="Manage issues.",
    )
    review_parsers = _create_category_parsers(
        plug.CoreCommand.reviews,
        help="Manage peer reviews.",
        description="Manage peer reviews.",
    )
    config_parsers = _create_category_parsers(
        plug.CoreCommand.config,
        help="Configure RepoBee.",
        description="Configure RepoBee.",
    )

    _add_repo_parsers(
        base_parser, base_student_parser, master_org_parser, repo_parsers
    )
    _add_issue_parsers(
        [base_parser, base_student_parser, _REPO_NAME_PARSER], issues_parsers
    )
    _add_peer_review_parsers(
        [base_parser, base_student_parser, _REPO_NAME_PARSER], review_parsers
    )
    _add_config_parsers(base_parser, master_org_parser, config_parsers)

    return _add_extension_parsers(
        subparsers,
        ext_commands,
        base_parser,
        base_student_parser,
        master_org_parser,
        _REPO_NAME_PARSER,
        categories,
        config._read_config(config_file) if config_file.is_file() else {},
        show_all_opts,
    )


def _add_repo_parsers(
    base_parser, base_student_parser, master_org_parser, repo_parsers
):
    repo_parsers.add_parser(
        plug.CoreCommand.repos.setup.name,
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
            _REPO_NAME_PARSER,
            _HOOK_RESULTS_PARSER,
        ],
        formatter_class=_OrderedFormatter,
    )

    update = repo_parsers.add_parser(
        plug.CoreCommand.repos.update.name,
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
            _REPO_NAME_PARSER,
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

    clone = repo_parsers.add_parser(
        plug.CoreCommand.repos.clone.name,
        help="Clone student repos.",
        description="Clone student repos asynchronously in bulk.",
        parents=[
            base_parser,
            base_student_parser,
            _REPO_DISCOVERY_PARSER,
            _HOOK_RESULTS_PARSER,
        ],
        formatter_class=_OrderedFormatter,
    )

    for task in plug.manager.hook.clone_task():
        util.call_if_defined(task.add_option, clone)

    plug.manager.hook.clone_parser_hook(clone_parser=clone)

    repo_parsers.add_parser(
        plug.CoreCommand.repos.create_teams.name,
        help="Create student teams without creating repos.",
        description=(
            "Only create student teams. This is intended for when you want to "
            "use RepoBee for management, but don't want to dictate the names "
            "of your student's repositories. The `setup` command performs "
            "this step automatically, so there is never a need to run both "
            "this command AND `setup`."
        ),
        parents=[base_parser, base_student_parser],
        formatter_class=_OrderedFormatter,
    )

    repo_parsers.add_parser(
        plug.CoreCommand.repos.migrate.name,
        help="Migrate repositories into the target organization.",
        description=(
            "Migrate repositories into the target organization. "
            "The repos must be local on disk to be migrated. Note that "
            "migrated repos will be private."
        ),
        parents=[_REPO_NAME_PARSER, base_parser],
        formatter_class=_OrderedFormatter,
    )


def _add_config_parsers(base_parser, master_org_parser, config_parsers):
    show_config = config_parsers.add_parser(
        plug.CoreCommand.config.show.name,
        help="Show the configuration file",
        description=(
            "Show the contents of the configuration file. If no configuration "
            "file can be found, show the path where repobee expectes to find "
            "it."
        ),
        formatter_class=_OrderedFormatter,
    )
    _add_traceback_arg(show_config)

    config_parsers.add_parser(
        plug.CoreCommand.config.verify.name,
        help="Verify core settings.",
        description="Verify core settings by trying various API requests.",
        parents=[base_parser, master_org_parser],
        formatter_class=_OrderedFormatter,
    )


def _add_peer_review_parsers(base_parsers, review_parsers):
    assign_parser = review_parsers.add_parser(
        plug.CoreCommand.reviews.assign.name,
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
    check_review_progress = review_parsers.add_parser(
        plug.CoreCommand.reviews.check.name,
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
    review_parsers.add_parser(
        plug.CoreCommand.reviews.end.name,
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


def _add_issue_parsers(base_parsers, issue_parsers):
    base_parser, base_student_parser, master_org_parser = base_parsers
    open_parser = issue_parsers.add_parser(
        plug.CoreCommand.issues.open.name,
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

    close_parser = issue_parsers.add_parser(
        plug.CoreCommand.issues.close.name,
        description=(
            "Close issues in student repos based on a regex. For each master "
            "repository specified, the student list is traversed. For every "
            "student repo found, any open issues matching the `--title-regex` "
            "are closed."
        ),
        help="Close issues in student repos.",
        parents=[base_parser, base_student_parser, _REPO_DISCOVERY_PARSER],
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

    list_parser = issue_parsers.add_parser(
        plug.CoreCommand.issues.list.name,
        description="List issues in student repos.",
        help="List issues in student repos.",
        parents=[
            base_parser,
            base_student_parser,
            _REPO_DISCOVERY_PARSER,
            _HOOK_RESULTS_PARSER,
        ],
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
    have to be disabled for future versions, but it works for 3.6, 3.7 and 3.8
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


def _add_extension_parsers(
    subparsers,
    ext_commands,
    base_parser,
    base_student_parser,
    master_org_parser,
    repo_name_parser,
    categories,
    parsed_config,
    show_all_opts,
):
    """Add extension parsers defined by plugins."""
    if not ext_commands:
        return []
    for cmd in ext_commands:
        parents = []
        bp = plug.BaseParser
        req_parsers = cmd.requires_base_parsers or []
        if cmd.requires_api or bp.BASE in req_parsers:
            parents.append(base_parser)
        if bp.STUDENTS in req_parsers:
            parents.append(base_student_parser)
        if bp.MASTER_ORG in req_parsers:
            parents.append(master_org_parser)

        if bp.REPO_DISCOVERY in req_parsers:
            parents.append(_REPO_DISCOVERY_PARSER)
        elif bp.REPO_NAMES in req_parsers:
            parents.append(repo_name_parser)

        cmd_parser = (
            cmd.parser(parsed_config, show_all_opts)
            if callable(cmd.parser)
            else cmd.parser
        )
        parents.append(cmd_parser)

        category_parsers = categories.get(cmd.category) or subparsers
        ext_parser = category_parsers.add_parser(
            cmd.name,
            help=cmd.help,
            description=cmd.description,
            parents=parents,
            formatter_class=_OrderedFormatter,
        )
        try:
            _add_traceback_arg(ext_parser)
        except argparse.ArgumentError:
            pass

        ext_parser.add_argument(
            "--repobee-action",
            action="store_const",
            help=argparse.SUPPRESS,
            const=cmd.name,
            default=cmd.name,
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
        if category_parsers == subparsers:
            # in this case it's a category action, and we must add the category
            ext_parser.add_argument(
                "--repobee-category",
                action="store_const",
                help=argparse.SUPPRESS,
                const=cmd.name,
                default=cmd.name,
                dest="category",
            )

    return ext_commands


def _create_base_parsers(show_all_opts, config_file):
    """Create the base parsers."""
    configured_defaults = config.get_configured_defaults(config_file)

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
            "Access token for the platform instance. Can also be specified in "
            "the `{}` environment variable.".format(constants.TOKEN_ENV)
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
        "-t",
        "--token",
        help=token_help,
        type=str,
        required=not configured("token") and api_requires("token"),
        default=default("token"),
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
