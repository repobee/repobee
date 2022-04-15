"""WIP rewrite of the repos category.

.. module:: repos
    :synopsis: Implementations of the repos category of commands.
"""
import pathlib
import repobee_plug as plug

from _repobee import command
from _repobee.fileutil import DirectoryLayout


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


def students_option():
    return plug.cli.option(
        "-s",
        "--students",
        help="one or more whitespace separated student usernames",
        configurable=True,
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


class CloneCommand(plug.Plugin, plug.cli.Command):
    _is_core_command = True

    __settings__ = plug.cli.command_settings(
        action=plug.cli.CoreCommand.repos.clone,
        help="clone repos",
        description="Clone repos.",
        config_section_name="repobee",
    )

    update_local = plug.cli.flag(
        help="attempt to update local student repositories, "
        "stashing any unstaged changes (beta feature)",
    )

    directory_layout = plug.cli.option(
        "--dl",
        "--directory-layout",
        help="how to arrange cloned repositories",
        converter=DirectoryLayout,
        argparse_kwargs=dict(
            choices=list(DirectoryLayout),
        ),
        default=DirectoryLayout.BY_TEAM,
    )

    repo_discovery_mutex = repo_discovery_mutex()

    students = students_option()

    students_file = students_file_option()

    hook_results_file = hook_results_file_option()

    def command(self, api: plug.PlatformAPI):
        return command.clone_repos(
            self.args.repos,
            self.args.update_local,
            self.args.directory_layout,
            api,
        )

    def handle_config(self, config: plug.Config) -> None:
        self._config = config


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


class SetupCommand(plug.Plugin, plug.cli.Command):
    _is_core_command = True

    __settings__ = plug.cli.command_settings(
        action=plug.cli.CoreCommand.repos.setup,
        help="setup student repos and associated teams",
        description="""Setup student repositories based on master repositories.
This command performs three primary actions: sets up the student teams,
creates one student repository for each master repository and finally
pushes the master repo files to the corresponding student repos. It is
perfectly safe to run this command several times, as any previously
performed step will simply be skipped.""",
        config_section_name="repobee",
    )

    assignments = assignments_option()

    students = students_option()

    students_file = students_file_option()

    template_org_name = template_org_name_option()

    allow_local_templates = allow_local_templates_option()

    hook_results_file = hook_results_file_option()

    def command(self, api: plug.PlatformAPI):
        return command.setup_student_repos(
            self.args.template_repo_urls, self.args.students, api
        )


def issue_option():
    return plug.cli.option(
        "-i",
        "--issue",
        help="path to issue file to open in repos to which pushes fail "
        "(NOTE: First line is assumed to be the title)",
    )


class UpdateCommand(plug.Plugin, plug.cli.Command):
    _is_core_command = True

    __settings__ = plug.cli.command_settings(
        action=plug.cli.CoreCommand.repos.update,
        help="update existing student repos",
        description="""Push changes from master repos to student repos. If the
`--issue` option is provided, the specified issue is opened in any repo
to which pushes fail (because the students have pushed something already).""",
        config_section_name="repobee",
    )

    assignments = assignments_option()

    students = students_option()

    students_file = students_file_option()

    template_org_name = template_org_name_option()

    allow_local_templates = allow_local_templates_option()

    issue = issue_option()

    def command(self, api: plug.PlatformAPI):
        return command.update_student_repos(
            self.args.template_repo_urls,
            self.args.students,
            api,
            self.args.issue,
        )


class MigrateCommand(plug.Plugin, plug.cli.Command):
    _is_core_command = True

    __settings__ = plug.cli.command_settings(
        action=plug.cli.CoreCommand.repos.migrate,
        help="migrate repositories into the target organization",
        description="""Migrate repositories into the target organization. The
repos must be local on disk to be migrated. Note that migrated repos
will be private.""",
        config_section_name="repobee",
    )

    assignments = assignments_option()

    allow_local_templates = allow_local_templates_option()

    def command(self, api: plug.PlatformAPI):
        return command.migrate_repos(self.args.template_repo_urls, api)
