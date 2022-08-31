"""Options in common for the core commands."""
import pathlib

import repobee_plug as plug


def repo_discovery_mutex():
    return plug.cli.mutually_exclusive_group(
        assignments=assignments_option(),
        discover_repos=plug.cli.flag(
            help="discover all repositories for the specified students (NOTE: "
            "expensive in terms of API calls)",
        ),
    )


def assignments_option():
    return plug.cli.option(
        "-a",
        "--assignments",
        help="one or more names of assignments",
        argparse_kwargs=dict(nargs="+"),
    )


def hook_results_file_option():
    return plug.cli.option(
        help="path to a .json file to store results from plugin hooks in"
    )


def students_mutex():
    return plug.cli.mutually_exclusive_group(
        students=students_option(),
        students_file=students_file_option(),
        __required__=True,
    )


def students_option():
    return plug.cli.option(
        "-s",
        "--students",
        help="one or more whitespace separated student usernames",
        argparse_kwargs=dict(nargs="+"),
    )


def students_file_option():
    return plug.cli.option(
        "--sf",
        "--students-file",
        help="path to a list of student usernames or groups of students",
        converter=pathlib.Path,
        configurable=True,
    )


def allow_local_templates_option():
    return plug.cli.flag(
        "--allow-local-templates",
        help="allow the use of template repos in the current working directory",
    )


def template_org_name_option():
    return plug.cli.option(
        "--to",
        "--template-org-name",
        help="name of the organization containing the template repos",
        configurable=True,
    )
