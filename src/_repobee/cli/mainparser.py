"""Definition of the primary parser for RepoBee.

.. module:: mainparser
    :synopsis: The primary parser for RepoBee.

.. moduleauthor:: Simon Larsén
"""

import types
import argparse
import pathlib

import repobee_plug as plug

import _repobee
from _repobee import plugin
from _repobee import config

from _repobee.cli import argparse_ext

from _repobee.cli import pluginparsers

__all__ = ["create_parser", "create_parser_for_docs"]

_HOOK_RESULTS_PARSER = argparse_ext.RepobeeParser(
    is_core_command=True, add_help=False
)
_HOOK_RESULTS_PARSER.add_argument(
    "--hook-results-file",
    help="path to a .json file to store results from plugin hooks in",
    type=str,
    default=None,
)
_REPO_NAME_PARSER = argparse_ext.RepobeeParser(
    is_core_command=True, add_help=False
)
_REPO_NAME_PARSER.add_argument(
    "-a",
    "--assignments",
    help="one or more names of assignments",
    type=str,
    required=True,
    nargs="+",
    dest="assignments",
)
_REPO_DISCOVERY_PARSER = argparse_ext.RepobeeParser(
    is_core_command=True, add_help=False
)
_DISCOVERY_MUTEX_GRP = _REPO_DISCOVERY_PARSER.add_mutually_exclusive_group(
    required=True
)
_DISCOVERY_MUTEX_GRP.add_argument(
    "-a",
    "--assignments",
    help="one or more names of assignments",
    type=str,
    nargs="+",
    dest="assignments",
)
_DISCOVERY_MUTEX_GRP.add_argument(
    "--discover-repos",
    help="discover all repositories for the specified students (NOTE: "
    "expensive in terms of API calls)",
    action="store_true",
)
_LOCAL_TEMPLATES_PARSER = argparse_ext.RepobeeParser(
    is_core_command=True, add_help=False
)
_LOCAL_TEMPLATES_PARSER.add_argument(
    "--allow-local-templates",
    help="allow the use of template repos in the current working directory",
    action="store_true",
)


def create_parser_for_docs() -> argparse.ArgumentParser:
    """Create a parser showing all options for the default CLI
    documentation.

    Returns:
        The primary parser, specifically for generating documentation.
    """
    plugin.initialize_default_plugins()
    plugin.initialize_dist_plugins(force=True)
    return create_parser(config_file=_repobee.constants.DEFAULT_CONFIG_FILE)


def create_parser(config_file: pathlib.Path) -> argparse.ArgumentParser:
    """Create the primary parser.

    Args:
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
    program_description += "Loaded plugins: " + loaded_plugins

    parser = argparse.ArgumentParser(
        prog="repobee",
        description=program_description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="display version info",
        action="version",
        version="{}".format(_repobee.__version__),
    )
    _add_subparsers(parser, config_file)

    return parser


def _add_subparsers(parser, config_file):
    """Add all of the subparsers to the parser. Note that the parsers prefixed
    with `base_` do not have any parent parsers, so any parser inheriting from
    them must also inherit from the required `base_parser` (unless it is a
    `base_` prefixed parser, of course).
    """

    (
        base_parser,
        base_student_parser,
        template_org_parser,
    ) = _create_base_parsers(config_file)

    subparsers = parser.add_subparsers(dest=argparse_ext.CATEGORY_DEST)
    subparsers.required = True
    parsers = {}

    def _create_category_parsers(category, help, description):
        category_command = subparsers.add_parser(
            name=category.name, help=help, description=description
        )
        category_parsers = category_command.add_subparsers(
            dest=argparse_ext.ACTION_DEST
        )
        category_parsers.required = True
        parsers[category] = category_parsers
        return category_parsers

    repo_parsers = _create_category_parsers(
        plug.cli.CoreCommand.repos,
        description="Manage repositories.",
        help="manage repositories",
    )
    teams_parsers = _create_category_parsers(
        plug.cli.CoreCommand.teams,
        description="Manage teams.",
        help="manage teams",
    )
    issues_parsers = _create_category_parsers(
        plug.cli.CoreCommand.issues,
        description="Manage issues.",
        help="manage issues",
    )
    review_parsers = _create_category_parsers(
        plug.cli.CoreCommand.reviews,
        help="manage peer reviews",
        description="Manage peer reviews.",
    )
    config_parsers = _create_category_parsers(
        plug.cli.CoreCommand.config,
        help="configure RepoBee",
        description="Configure RepoBee.",
    )

    def _add_action_parser(category_parsers):
        def inner(action, **kwargs):
            parsers[action] = category_parsers.add_parser(
                action.name, **kwargs
            )
            return parsers[action]

        return inner

    _add_repo_parsers(
        base_parser,
        base_student_parser,
        template_org_parser,
        _add_action_parser(repo_parsers),
    )
    _add_teams_parsers(
        base_parser,
        base_student_parser,
        template_org_parser,
        _add_action_parser(teams_parsers),
    )
    _add_issue_parsers(
        [base_parser, base_student_parser, _REPO_NAME_PARSER],
        _add_action_parser(issues_parsers),
    )
    _add_peer_review_parsers(
        [base_parser, base_student_parser, _REPO_NAME_PARSER],
        _add_action_parser(review_parsers),
    )
    _add_config_parsers(
        base_parser, template_org_parser, _add_action_parser(config_parsers)
    )

    pluginparsers.add_plugin_parsers(
        subparsers,
        argparse_ext.BaseParsers(
            base_parser=base_parser,
            student_parser=base_student_parser,
            template_org_parser=template_org_parser,
            repo_name_parser=_REPO_NAME_PARSER,
            repo_discovery_parser=_REPO_DISCOVERY_PARSER,
        ),
        parsers,
        config._read_config(config_file) if config_file.is_file() else {},
    )


def _add_repo_parsers(
    base_parser, base_student_parser, template_org_parser, add_parser
):
    add_parser(
        plug.cli.CoreCommand.repos.setup,
        help="setup student repos and associated teams",
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
            template_org_parser,
            _REPO_NAME_PARSER,
            _HOOK_RESULTS_PARSER,
            _LOCAL_TEMPLATES_PARSER,
        ],
        formatter_class=argparse_ext.OrderedFormatter,
    )

    update = add_parser(
        plug.cli.CoreCommand.repos.update,
        help="update existing student repos",
        description=(
            "Push changes from master repos to student repos. If the "
            "`--issue` option is provided, the specified issue is opened in "
            "any repo to which pushes fail (because the students have pushed "
            "something already)."
        ),
        parents=[
            base_parser,
            base_student_parser,
            template_org_parser,
            _REPO_NAME_PARSER,
            _LOCAL_TEMPLATES_PARSER,
        ],
        formatter_class=argparse_ext.OrderedFormatter,
    )
    update.add_argument(
        "-i",
        "--issue",
        help="path to issue file to open in repos to which pushes fail "
        "(NOTE: first line is assumed to be the title)",
        type=str,
    )

    clone = add_parser(
        plug.cli.CoreCommand.repos.clone,
        help="clone student repos",
        description="Clone student repos asynchronously in bulk.",
        parents=[
            base_parser,
            base_student_parser,
            _REPO_DISCOVERY_PARSER,
            _HOOK_RESULTS_PARSER,
        ],
        formatter_class=argparse_ext.OrderedFormatter,
    )
    clone.add_argument(
        "--update-local",
        help="attempt to update local student repositories, "
        "stashing any unstaged changes (beta feature)",
        action="store_true",
    )

    add_parser(
        plug.cli.CoreCommand.repos.migrate,
        help="migrate repositories into the target organization",
        description=(
            "Migrate repositories into the target organization. "
            "The repos must be local on disk to be migrated. Note that "
            "migrated repos will be private."
        ),
        parents=[_REPO_NAME_PARSER, base_parser, _LOCAL_TEMPLATES_PARSER],
        formatter_class=argparse_ext.OrderedFormatter,
    )


def _add_teams_parsers(
    base_parser, base_student_parser, template_org_parser, add_parser
):

    add_parser(
        plug.cli.CoreCommand.teams.create,
        help="create student teams without creating repos",
        description=(
            "Only create student teams. This is intended for when you want to "
            "use RepoBee for management, but don't want to dictate the names "
            "of your student's repositories. The `setup` command performs "
            "this step automatically, so there is never a need to run both "
            "this command AND `setup`."
        ),
        parents=[base_parser, base_student_parser],
        formatter_class=argparse_ext.OrderedFormatter,
    )


def _add_config_parsers(base_parser, template_org_parser, add_parser):
    show_config = add_parser(
        plug.cli.CoreCommand.config.show,
        help="show the configuration file",
        description=(
            "Show the contents of the configuration file. If no configuration "
            "file can be found, show the path where repobee expectes to find "
            "it."
        ),
        formatter_class=argparse_ext.OrderedFormatter,
    )
    show_config.add_argument(
        "--secrets",
        help="show secrets in the config file that are otherwise sanitized",
        action="store_true",
    )
    argparse_ext.add_debug_args(show_config)

    add_parser(
        plug.cli.CoreCommand.config.verify,
        help="verify core settings",
        description="Verify core settings by trying various API requests.",
        parents=[base_parser, template_org_parser],
        formatter_class=argparse_ext.OrderedFormatter,
    )


def _add_peer_review_parsers(base_parsers, add_parser):
    assign_parser = add_parser(
        plug.cli.CoreCommand.reviews.assign,
        description=(
            "For each student repo, create a review team with read access "
            "named <student-repo-name>-review and randomly assign "
            "other students to it. All students are assigned to the same "
            "amount of review teams, as specified by `--num-reviews`. Note "
            "that `--num-reviews` must be strictly less than the amount of "
            "students. Note that review allocation strategy may be altered "
            "by plugins."
        ),
        help="assign students to peer review each others' repos",
        parents=base_parsers,
        formatter_class=argparse_ext.OrderedFormatter,
    )
    assign_parser.add_argument(
        "-n",
        "--num-reviews",
        metavar="N",
        help="assign each student to review n repos, n < amount of students",
        type=int,
        default=1,
    )
    assign_parser.add_argument(
        "-i",
        "--issue",
        help="path to an issue file with review instructions to open in "
        "student repos (NOTE: first line is assumed to be the title)",
        type=str,
    )
    check_review_progress = add_parser(
        plug.cli.CoreCommand.reviews.check,
        description=(
            "Check which students have opened review review issues in their "
            "assigned repos. As it is possible for students to leave the peer "
            "review teams on their own, the command checks that each student "
            "is assigned to the expected amound of teams. There is currently "
            "no way to check if students have been swapped around, so using "
            "this command fow grading purposes is not recommended."
        ),
        help="check which students have opened peer review issues",
        parents=base_parsers,
        formatter_class=argparse_ext.OrderedFormatter,
    )
    check_review_progress.add_argument(
        "-r",
        "--title-regex",
        help="issues matching this regex will count as review issues.",
        required=True,
    )
    check_review_progress.add_argument(
        "-n",
        "--num-reviews",
        metavar="N",
        help="the expected amount of reviews each student should be assigned,"
        " used to check for team tampering",
        type=int,
        required=True,
    )
    add_parser(
        plug.cli.CoreCommand.reviews.end,
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
        help="delete review allocations created by `assign-reviews` "
        "(DESTRUCTIVE ACTION: read help section before using)",
        parents=base_parsers,
        formatter_class=argparse_ext.OrderedFormatter,
    )


def _add_issue_parsers(base_parsers, add_parser):
    base_parser, base_student_parser, template_org_parser = base_parsers
    open_parser = add_parser(
        plug.cli.CoreCommand.issues.open,
        description=(
            "Open issues in student repositories. For each master repository "
            "specified, the student list is traversed. For every student repo "
            "found, the issue specified by the `--issue` option is opened. "
            "NOTE: The first line of the issue file is assumed to be the "
            "issue title!"
        ),
        help="open issues in student repos",
        parents=base_parsers,
        formatter_class=argparse_ext.OrderedFormatter,
    )
    open_parser.add_argument(
        "-i",
        "--issue",
        help="path to an issue file (NOTE: first line is assumed to be the "
        "title)",
        type=str,
        required=True,
    )

    close_parser = add_parser(
        plug.cli.CoreCommand.issues.close,
        description=(
            "Close issues in student repos based on a regex. For each master "
            "repository specified, the student list is traversed. For every "
            "student repo found, any open issues matching the `--title-regex` "
            "are closed."
        ),
        help="close issues in student repos",
        parents=[base_parser, base_student_parser, _REPO_DISCOVERY_PARSER],
        formatter_class=argparse_ext.OrderedFormatter,
    )
    close_parser.add_argument(
        "-r",
        "--title-regex",
        help="regex to filter issues by",
        type=str,
        required=True,
    )

    list_parser = add_parser(
        plug.cli.CoreCommand.issues.list,
        description="List issues in student repos.",
        help="List issues in student repos.",
        parents=[
            base_parser,
            base_student_parser,
            _REPO_DISCOVERY_PARSER,
            _HOOK_RESULTS_PARSER,
        ],
        formatter_class=argparse_ext.OrderedFormatter,
    )
    list_parser.add_argument(
        "-r", "--title-regex", help="regex to filter issues by"
    )
    list_parser.add_argument(
        "-b",
        "--show-body",
        action="store_true",
        help="show the body of the issue, alongside the default info",
    )
    list_parser.add_argument(
        "--author",
        help="only show issues by this author",
        type=str,
        default=None,
    )
    state = list_parser.add_mutually_exclusive_group()
    state.add_argument(
        "--open",
        help="list open issues (default)",
        action="store_const",
        dest="state",
        const=plug.IssueState.OPEN,
    )
    state.add_argument(
        "--closed",
        help="list closed issues",
        action="store_const",
        dest="state",
        const=plug.IssueState.CLOSED,
    )
    state.add_argument(
        "--all",
        help="list all issues (open and closed)",
        action="store_const",
        dest="state",
        const=plug.IssueState.ALL,
    )
    list_parser.set_defaults(state=plug.IssueState.OPEN)


def _create_base_parsers(config_file):
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

    # API args help sections
    user_help = "your username"
    org_name_help = "name of the target organization"
    base_url_help = (
        "Base url to a platform API. Must be HTTPS. For example, with "
        "github.com, the base url is https://api.github.com, and with "
        "GitHub enterprise, the url is https://<ENTERPRISE_HOST>/api/v3"
    )
    token_help = "access token for the platform instance"

    # other configurable args help sections
    # these should not be checked against the api_requires function
    students_file_help = (
        "path to a list of student usernames or groups of students"
    )
    template_org_help = (
        "name of the organization containing the template repos "
        "(defaults to the same value as `-o|--org-name`)"
    )

    base_parser = argparse_ext.RepobeeParser(
        is_core_command=True, add_help=False
    )
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

    argparse_ext.add_debug_args(base_parser)
    # base parser for when student lists are involved
    base_student_parser = argparse_ext.RepobeeParser(
        is_core_command=True, add_help=False
    )
    students = base_student_parser.add_argument_group(
        "core"
    ).add_mutually_exclusive_group(required=not configured("students_file"))
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

    template_org_parser = argparse_ext.RepobeeParser(
        is_core_command=True, add_help=False
    )
    template_org_parser.add_argument(
        "--to",
        "--template-org-name",
        help=template_org_help,
        default=default("template_org_name"),
        dest="template_org_name",
    )

    return (base_parser, base_student_parser, template_org_parser)
