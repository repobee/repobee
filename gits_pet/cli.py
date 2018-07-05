"""CLI module.

This module the CLI for gits_pet.
"""

import argparse
import configparser
import os
import sys
import appdirs
import gits_pet
import logging
import daiquiri

from contextlib import contextmanager

from gits_pet import admin
from gits_pet import github_api
from gits_pet import git
from gits_pet import util

daiquiri.setup(
    level=logging.INFO,
    outputs=(
        daiquiri.output.Stream(
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="[%(levelname)s] %(message)s")),
        daiquiri.output.File(
            filename="{}.log".format(__file__),
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="%(asctime)s [PID %(process)d] [%(levelname)s] "
                "%(name)s -> %(message)s")),
    ))

LOGGER = daiquiri.getLogger(__file__)
SUB = 'subparser'
SETUP_PARSER = 'setup'
UPDATE_PARSER = 'update'
MIGRATE_PARSER = 'migrate'
ADD_TO_TEAMS_PARSER = 'add-to-teams'
OPEN_ISSUE_PARSER = 'open-issue'
CLOSE_ISSUE_PARSER = 'close-issue'

CONFIG_DIR = appdirs.user_config_dir(
    appname=__package__,
    appauthor=gits_pet.__author__,
    version=gits_pet.__version__)

# arguments that can be configured via config file
CONFIGURABLE_ARGS = set(('user', 'org_name', 'github_base_url',
                         'students_file'))


def read_config(config_file="{}/config.cnf".format(CONFIG_DIR)):
    config_parser = configparser.ConfigParser()
    if os.path.isfile(config_file):
        LOGGER.info("found configuration file at {}".format(config_file))
        config_parser.read(config_file)
    return config_parser["DEFAULT"]


def add_issue_parsers(base_parser, subparsers):
    issue_parser_base = argparse.ArgumentParser(
        add_help=False, parents=[base_parser])

    open_parser = subparsers.add_parser(
        OPEN_ISSUE_PARSER,
        description=(
            "Open issues in student repositories. For each master repository "
            "specified, the student list is traversed. For every student repo "
            "found, the issue specified by the `--issue` option is opened. "
            "NOTE: The first line of the issue file is assumed to be the "
            "issue title!"),
        help="Open issues in student repos.",
        parents=[issue_parser_base])
    open_parser.add_argument(
        '-i',
        '--issue',
        help=
        "Path to an issue. NOTE: The first line is assumed to be the title.",
        type=str,
        required=True)

    close_parser = subparsers.add_parser(
        CLOSE_ISSUE_PARSER,
        description=(
            "Close issues in student repos based on a regex. For each master "
            "repository specified, the student list is traversed. For every "
            "student repo found, any open issues matching the `--title-regex` "
            "are closed."),
        help="Close issues in student repos.",
        parents=[issue_parser_base])
    close_parser.add_argument(
        '-r',
        '--title-regex',
        help=(
            "Regex to match titles against. Any issue whose title matches the "
            "regex will be closed."),
        type=str,
        required=True)


def create_parser():
    configured_defaults = get_configured_defaults()
    LOGGER.info("config file defaults:\n{}".format("\n   ".join([""] + [
        "{}: {}".format(key, value)
        for key, value in configured_defaults.items()
        if key in CONFIGURABLE_ARGS
    ] + [""])))
    default = lambda arg_name: configured_defaults[arg_name] if arg_name in configured_defaults else None

    is_required = lambda arg_name: True if arg_name not in configured_defaults else False

    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        '-o',
        '--org-name',
        help="Name of the organization to which repos should be added.",
        type=str,
        required=is_required('org_name'),
        default=default('org_name'))
    base_parser.add_argument(
        '-g',
        '--github-base-url',
        help=
        "Base url to a GitHub v3 API. For enterprise, this is `https://<HOST>/api/v3",
        type=str,
        required=is_required('github_base_url'),
        default=default('github_base_url'))

    url_parser = argparse.ArgumentParser(add_help=False, parents=[base_parser])
    names_or_urls = url_parser.add_mutually_exclusive_group(required=True)
    names_or_urls.add_argument(
        '-mu',
        '--master-repo-urls',
        help=(
            "One or more URLs to the master repositories. One student repo is "
            "created for each master repo."),
        type=str,
        nargs='+')
    names_or_urls.add_argument(
        '-mn',
        '--master-repo-names',
        help=("One or more names of master repositories. Assumes that the "
              "master repos are in the same organization as specified by "
              "the 'org-name' argument."),
        type=str,
        nargs='+')

    # base parser for when student lists are involved
    base_student_parser = argparse.ArgumentParser(add_help=False)
    students = base_student_parser.add_mutually_exclusive_group(
        required=is_required('students_file'))
    students.add_argument(
        '-sf',
        '--students-file',
        help="Path to a list of student usernames.",
        type=str,
        default=default('students_file'))
    students.add_argument(
        '-s',
        '--students',
        help='One or more whitespace separated student usernames.',
        type=str,
        nargs='+')

    # base parser for when files need to be pushed
    base_push_parser = argparse.ArgumentParser(add_help=False)

    # the username is required for any pushing
    base_push_parser.add_argument(
        '-u',
        '--user',
        help=
        "Your GitHub username. Needed for pushing without CLI interaction.",
        type=str,
        required=is_required('user'),
        default=default('user'))

    parser = argparse.ArgumentParser(
        prog='gits_pet',
        description='A CLI tool for administrating student repositories.')

    subparsers = parser.add_subparsers(dest=SUB)
    subparsers.required = True

    create = subparsers.add_parser(
        SETUP_PARSER,
        help="Setup student repos.",
        description=
        ("Setup student repositories based on master repo templates. This "
         "command performs three primary actions: sets up the student teams, "
         "creates one student repository for each master repository and "
         "finally pushes the master repo files to the corresponding student "
         "repos. It is perfectly safe to run this command several times, as "
         "any previously performed step will simply be skipped. The master "
         "repo is assumed to be located in the target organization, and will "
         "be temporarily cloned to disk for the duration of the command. "),
        parents=[base_push_parser, base_student_parser, url_parser])

    update = subparsers.add_parser(
        UPDATE_PARSER,
        help="Update existing student repos.",
        description=(
            "Push changes from master repos to student repos. The master repos "
            "must be available within the organization. They can be added "
            "manually, or with the `migrate-repos` command."),
        parents=[base_push_parser, base_student_parser, url_parser])
    update.add_argument(
        '-i',
        '--issue',
        help=
        ("Path to issue to open in repos to which update pushes fail. Assumes "
         "that the first line is the title."),
        type=str,
    )

    migrate = subparsers.add_parser(
        MIGRATE_PARSER,
        help="Migrate master repositories into the target organization.",
        description=
        ("Migrate master repositories into the target organization. gits_pet "
         "relies on the master repositories being located in the target "
         "organization. This command facilitates moving repositories from "
         "somewhere on the same GitHub instance (e.g. on github.com or your "
         "own GitHub Enterprise server) into the organization. Each "
         "master repository specified with `-mu` is cloned to disk, a repo "
         "with the same name is created in the target organization, and then "
         "the files are pushed to the new repo. All of the master repos are"
         "added to the `{}` team. ".format(admin.MASTER_TEAM) + \
         "NOTE: `migrate-repos` can also be used to update already migrated repos "
         "that have been changed in their original repos."
         ),
        parents=[base_push_parser, url_parser])

    add_to_teams = subparsers.add_parser(
        ADD_TO_TEAMS_PARSER,
        help=("Create student teams and add students to them. This command is "
              "automatically executed by the `setup` command."),
        description=
        ("Create student teams and add students to them. This command is "
         "automatically executed by the `setup` command. It exists mostly to "
         "be able to quickly add students to their teams if their accounts "
         "had not been activated at the time of creating the repositories. If "
         "you are unsure if all the other steps have been performed (repo "
         "creation, pushing files etc) for the students in question, run the "
         "`setup` command instead."),
        parents=[base_student_parser, base_parser])

    add_issue_parsers(base_student_parser, subparsers)

    return parser


def get_configured_defaults():
    config = read_config()
    configured = config.keys()
    if configured - CONFIGURABLE_ARGS:  # there are surpluss arguments
        raise ValueError("Config contains invalid keys: {}".format(
            ", ".join(configured - CONFIGURABLE_ARGS)))
    return config


@contextmanager
def _sys_exit_on_git_error():
    try:
        yield
    except git.PushFailedError as exc:
        LOGGER.error(
            "There was an error pushing to {}. Verify that your token has adequate access.".
            format(exc.url))
        sys.exit(1)
    except git.CloneFailedError as exc:
        LOGGER.error(
            "There was an error cloning from {}. Does the repo really exist?".
            format(exc.url))
        sys.exit(1)
    except git.GitError as exc:
        LOGGER.error("Something went wrong with git. See the logs for info.")
        sys.exit(1)


def main():
    parser = create_parser()
    args = parser.parse_args()

    # TODO add try/catch here with graceful exit
    api = github_api.GitHubAPI(args.github_base_url, git.OAUTH_TOKEN,
                               args.org_name)
    if 'students' in args and args.students:
        students = args.students
    elif 'students_file' in args and args.students_file:
        if not os.path.isfile(args.students_file):
            raise ValueError("'{}' is not a file".format(args.students_file))
        with open(args.students_file, 'r') as f:
            students = [student.strip() for student in f]

    # early exit for this parser as it lacks urls/names
    if getattr(args, SUB) == ADD_TO_TEAMS_PARSER:
        with _sys_exit_on_git_error():
            admin.add_students_to_teams(students, api)
        return

    if hasattr(args, 'issue') and args.issue:
        issue = util.read_issue(args.issue)
    else:
        issue = None

    if not args.master_repo_urls:
        assert args.master_repo_names
        # convert names urls
        master_urls = api.get_repo_urls(args.master_repo_names)
        master_names = args.master_repo_names
    else:
        master_urls = args.master_repo_urls
        master_names = [util.repo_name(url) for url in master_urls]

    if getattr(args, SUB) == SETUP_PARSER:
        with _sys_exit_on_git_error():
            admin.setup_student_repos(
                master_repo_urls=master_urls,
                students=students,
                user=args.user,
                api=api)
    elif getattr(args, SUB) == UPDATE_PARSER:
        with _sys_exit_on_git_error():
            admin.update_student_repos(master_urls, students, args.user, api)
    elif getattr(args, SUB) == OPEN_ISSUE_PARSER:
        with _sys_exit_on_git_error():
            admin.open_issue(master_names, students, issue, api)
    elif getattr(args, SUB) == CLOSE_ISSUE_PARSER:
        with _sys_exit_on_git_error():
            admin.close_issue(args.title_regex, master_names, students, api)
    elif getattr(args, SUB) == MIGRATE_PARSER:
        with _sys_exit_on_git_error():
            admin.migrate_repos(master_urls, args.user, api)
    else:
        raise ValueError("Illegal value for subparser: {}".format(
            getattr(args, SUB)))


if __name__ == "__main__":
    main()
