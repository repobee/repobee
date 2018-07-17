"""CLI module.

This module the CLI for gits_pet.
"""

import argparse
import configparser
import pathlib
import os
import sys
from contextlib import contextmanager
from typing import List, Iterable

import appdirs
import gits_pet
import logging
import daiquiri

from gits_pet import admin
from gits_pet import github_api
from gits_pet import git
from gits_pet import util
from gits_pet import tuples
from gits_pet import exception
from gits_pet import config

daiquiri.setup(
    level=logging.INFO,
    outputs=(
        daiquiri.output.Stream(
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="[%(levelname)s] %(message)s")),
        daiquiri.output.File(
            filename="{}.log".format(__package__),
            formatter=daiquiri.formatter.ColorFormatter(
                fmt="%(asctime)s [PID %(process)d] [%(levelname)s] "
                "%(name)s -> %(message)s")),
    ))

LOGGER = daiquiri.getLogger(__file__)
SUB = 'subparser'
SETUP_PARSER = 'setup'
UPDATE_PARSER = 'update'
CLONE_PARSER = 'clone'
MIGRATE_PARSER = 'migrate'
ADD_TO_TEAMS_PARSER = 'add-to-teams'
OPEN_ISSUE_PARSER = 'open-issue'
CLOSE_ISSUE_PARSER = 'close-issue'


def parse_args(sys_args: Iterable[str]) -> (tuples.Args, github_api.GitHubAPI):
    """Parse the command line arguments and initialize the GitHubAPI.
    
    Args:
        sys_args: A list of command line arguments.

    Returns:
        a tuples.Args namedtuple with the arguments, and an initialized
        GitHubAPI instance.
    """
    parser = _create_parser()
    args = parser.parse_args(sys_args)

    api = _connect_to_api(args.github_base_url, git.OAUTH_TOKEN, args.org_name)

    if 'master_repo_urls' in args and args.master_repo_urls:
        master_urls = args.master_repo_urls
        master_names = [util.repo_name(url) for url in master_urls]
    elif 'master_repo_names' in args and args.master_repo_names:
        master_names = args.master_repo_names
        master_urls = _repo_names_to_urls(master_names, api)
    else:
        master_urls = None
        master_names = None

    parsed_args = tuples.Args(
        subparser=getattr(args, SUB),
        org_name=args.org_name,
        github_base_url=args.github_base_url,
        user=args.user if 'user' in args else None,
        master_repo_urls=master_urls,
        master_repo_names=master_names,
        students=_extract_students(args),
        issue=util.read_issue(args.issue)
        if 'issue' in args and args.issue else None,
        title_regex=args.title_regex if 'title_regex' in args else None,
    )

    return parsed_args, api


def handle_parsed_args(args: tuples.Args, api: github_api.GitHubAPI):
    """Handle parsed CLI arguments and dispatch commands to the appropriate
    functions. Expected exceptions are caught and turned into SystemExit
    exceptions, while unexpected exceptions are allowed to propagate.

    Args:
        args: A namedtuple containing parsed command line arguments.
        api: An initialized GitHubAPI instance.
    """
    if args.subparser == ADD_TO_TEAMS_PARSER:
        with _sys_exit_on_expected_error():
            admin.add_students_to_teams(args.students, api)
    elif args.subparser == SETUP_PARSER:
        with _sys_exit_on_expected_error():
            admin.setup_student_repos(
                master_repo_urls=args.master_repo_urls,
                students=args.students,
                user=args.user,
                api=api)
    elif args.subparser == UPDATE_PARSER:
        with _sys_exit_on_expected_error():
            admin.update_student_repos(args.master_repo_urls, args.students,
                                       args.user, api)
    elif args.subparser == OPEN_ISSUE_PARSER:
        with _sys_exit_on_expected_error():
            admin.open_issue(args.master_repo_names, args.students, args.issue,
                             api)
    elif args.subparser == CLOSE_ISSUE_PARSER:
        with _sys_exit_on_expected_error():
            admin.close_issue(args.title_regex, args.master_repo_names,
                              args.students, api)
    elif args.subparser == MIGRATE_PARSER:
        with _sys_exit_on_expected_error():
            admin.migrate_repos(args.master_repo_urls, args.user, api)
    elif args.subparser == CLONE_PARSER:
        with _sys_exit_on_expected_error():
            admin.clone_repos(args.master_repo_names, args.students, api)
    else:
        raise ValueError("Illegal value for subparser: {}".format(
            args.subparser))


def _add_issue_parsers(base_parsers, subparsers):
    open_parser = subparsers.add_parser(
        OPEN_ISSUE_PARSER,
        description=(
            "Open issues in student repositories. For each master repository "
            "specified, the student list is traversed. For every student repo "
            "found, the issue specified by the `--issue` option is opened. "
            "NOTE: The first line of the issue file is assumed to be the "
            "issue title!"),
        help="Open issues in student repos.",
        parents=base_parsers)
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
        parents=base_parsers)
    close_parser.add_argument(
        '-r',
        '--title-regex',
        help=(
            "Regex to match titles against. Any issue whose title matches the "
            "regex will be closed."),
        type=str,
        required=True)


def _create_parser():
    """Create the parser. 
    """

    parser = argparse.ArgumentParser(
        prog='gits_pet',
        description='A CLI tool for administrating student repositories.')
    _add_subparsers(parser)
    return parser


def _add_subparsers(parser):
    """Add all of the subparsers to the parser. Note that the parsers prefixed
    with `base_` do not have any parent parsers, so any parser inheriting from
    them must also inherit from the required `base_parser` (unless it is a
    `base_` prefixed parser, of course)."""
    base_parser, base_student_parser, base_push_parser = _create_base_parsers()

    repo_name_parser = argparse.ArgumentParser(
        add_help=False, parents=[base_parser])
    repo_name_parser.add_argument(
        '-mn',
        '--master-repo-names',
        help=("One or more names of master repositories. Names must either "
              "refer to local directories, or to master repositories in the "
              "target organization."),
        type=str,
        required=True,
        nargs='+')

    subparsers = parser.add_subparsers(dest=SUB)
    subparsers.required = True

    create = subparsers.add_parser(
        SETUP_PARSER,
        help="Setup student repos.",
        description=
        ("Setup student repositories based on master repositories. This "
         "command performs three primary actions: sets up the student teams, "
         "creates one student repository for each master repository and "
         "finally pushes the master repo files to the corresponding student "
         "repos. It is perfectly safe to run this command several times, as "
         "any previously performed step will simply be skipped. The master "
         "repo is assumed to be located in the target organization, and will "
         "be temporarily cloned to disk for the duration of the command. "),
        parents=[base_push_parser, base_student_parser, repo_name_parser])

    update = subparsers.add_parser(
        UPDATE_PARSER,
        help="Update existing student repos.",
        description=(
            "Push changes from master repos to student repos. The master repos "
            "must be available within the organization. They can be added "
            "manually, or with the `migrate-repos` command."),
        parents=[base_push_parser, base_student_parser, repo_name_parser])
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
        parents=[base_parser, base_push_parser])
    names_or_urls = migrate.add_mutually_exclusive_group(required=True)
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

    clone = subparsers.add_parser(
        CLONE_PARSER,
        help="Clone student repos.",
        description="Clone student repos asynchronously in bulk.",
        parents=[base_student_parser, repo_name_parser])

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

    _add_issue_parsers([base_student_parser, repo_name_parser], subparsers)


def _create_base_parsers():
    """Create the base parsers."""
    configured_defaults = config.get_configured_defaults()
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
        "Base url to a GitHub v3 API. For enterprise, this is usually `https://<HOST>/api/v3`",
        type=str,
        required=is_required('github_base_url'),
        default=default('github_base_url'))

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

    return base_parser, base_student_parser, base_push_parser


@contextmanager
def _sys_exit_on_expected_error():
    """Expect either git.GitError or github_api.APIError."""
    try:
        yield
    except exception.PushFailedError as exc:
        LOGGER.error(
            "There was an error pushing to {}. Verify that your token has adequate access.".
            format(exc.url))
        sys.exit(1)
    except exception.CloneFailedError as exc:
        LOGGER.error(
            "There was an error cloning from {}. Does the repo really exist?".
            format(exc.url))
        sys.exit(1)
    except exception.GitError as exc:
        LOGGER.error("Something went wrong with git. See the logs for info.")
        sys.exit(1)
    except exception.APIError as exc:
        LOGGER.error("Exiting beacuse of {.__class__.__name__}".format(exc))
        sys.exit(1)


def _extract_students(args: argparse.Namespace) -> List[str]:
    """Extract students from args namespace.`

    Args:
        args: A namespace object.

    Returns:
        a list of student usernames, or None of neither `students` or
        `students_file` is in the namespace.
    """
    if 'students' in args and args.students:
        students = args.students
    elif 'students_file' in args and args.students_file:
        students_file = pathlib.Path(args.students_file)
        students_file.resolve()
        if not students_file.is_file():
            raise exception.FileError(
                "'{!s}' is not a file".format(students_file))
        if not students_file.stat().st_size:
            raise exception.FileError("'{!s}' is empty".format(students_file))
        students = [
            student.strip() for student in students_file.read_text(
                encoding=sys.getdefaultencoding()).split(os.linesep)
            if student  # skip blank lines
        ]
    else:
        students = None

    return students


def _connect_to_api(github_base_url: str, token: str,
                    org_name: str) -> github_api.GitHubAPI:
    """Return a GitHubAPI instance connected to the specified API endpoint."""
    try:
        api = github_api.GitHubAPI(github_base_url, token, org_name)
    except exception.NotFoundError:
        # more informative message
        raise exception.NotFoundError(
            "organization {} could not be found".format(org_name))
    return api


def _repo_names_to_urls(repo_names: Iterable[str],
                        api: github_api.GitHubAPI) -> List[str]:
    """Use the repo_names to extract urls to the repos. Look for repos with
    corresponding names in the current working directory, as well as in the
    target organization.

    Args:
        repo_names: names of repositories.
        api: A GitHubAPI instance.

    Returns:
        a list of urls corresponding to the repo_names.
    """
    urls, not_found = api.get_repo_urls(repo_names)
    LOGGER.info("found {} remote repos: {}".format(len(urls), urls))

    for name in not_found:
        local_path = os.path.abspath(name)
        if util.is_git_repo(local_path):
            LOGGER.info("found local repo {}".format(local_path))
            urls.append(pathlib.Path(local_path).as_uri())

    if len(urls) != len(repo_names):
        # TODO improve error message
        raise exception.ParseError("Could not find one or more master repos")
    return urls
