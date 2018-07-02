"""CLI module.

This module the CLI for gits_pet.
"""

import argparse
import configparser
import os
import appdirs
import gits_pet
import logging
import daiquiri

from gits_pet import admin
from gits_pet import github_api
from gits_pet import git

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
LOGGER.warning("babla")
SUB = 'subparser'
CREATE_PARSER = 'create'

CONFIG_DIR = appdirs.user_config_dir(
    appname=__package__,
    appauthor=gits_pet.__author__,
    version=gits_pet.__version__)

# arguments that can be configured via config file
CONFIGURABLE_ARGS = set(('user', 'org_name', 'github_base_url'))


def read_config(config_file="{}/config.cnf".format(CONFIG_DIR)):
    config_parser = configparser.ConfigParser()
    if os.path.isfile(config_file):
        config_parser.read(config_file)
    return config_parser["DEFAULT"]


def create_parser():
    parser = argparse.ArgumentParser(
        prog='gits_pet',
        description='A CLI tool for administrating student repositories.')

    subparsers = parser.add_subparsers(dest=SUB)
    subparsers.required = True

    configured_defaults = get_configured_defaults()

    is_required = lambda arg_name: True if arg_name not in configured_defaults else False

    create = subparsers.add_parser(CREATE_PARSER, help='Create student repos.')

    names_or_urls = create.add_mutually_exclusive_group(required=True)
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
    create.add_argument(
        '-u',
        '--user',
        help=
        "Your GitHub username. Needed for pushing without CLI interaction.",
        type=str,
        required=is_required('user'))
    create.add_argument(
        '-o',
        '--org-name',
        help="Name of the organization to which repos should be added.",
        type=str,
        required=is_required('org_name'))
    create.add_argument(
        '-g',
        '--github-base-url',
        help=
        "Base url to a GitHub v3 API. For enterprise, this is `https://<HOST>/api/v3",
        type=str,
        required=is_required('github_base_url'))
    create.add_argument(
        '-s',
        '--student-list',
        help="Path to a list of student usernames.",
        required=True)

    create.set_defaults(**configured_defaults)
    LOGGER.info("config file defaults:\n{}".format("\n".join([
        "{}: {}".format(key, value)
        for key, value in configured_defaults.items()
    ])))

    return parser


def get_configured_defaults():
    config = read_config()
    configured = config.keys()
    if configured - CONFIGURABLE_ARGS:  # there are surpluss arguments
        raise ValueError("Config contains invalid keys: {}".format(
            ", ".join(configured - CONFIGURABLE_ARGS)))
    return config


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not os.path.isfile(args.student_list):
        raise ValueError("'{}' is not a file".format(args.student_list))
    with open(args.student_list, 'r') as f:
        students = [student.strip() for student in f]

    if not args.master_repo_urls:
        assert args.master_repo_names
        # convert names urls
        api = github_api.GitHubAPI(args.github_base_url, git.OAUTH_TOKEN,
                                   args.org_name)
        master_urls = api.get_repo_urls(args.master_repo_names)
    else:
        master_urls = args.master_repo_urls

    admin.create_multiple_student_repos(master_urls, args.user, students,
                                        args.org_name,
                                        args.github_base_url)


if __name__ == "__main__":
    main()
