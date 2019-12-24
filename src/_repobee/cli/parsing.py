"""Parsing logic for RepoBee's primary parser.

This is separated into its own module as it is a relatively complex affair.
Any non-trivial parsing logic should go in here, whereas definitions of
the primary parser should go int :py:mod:`_repobee.cli.mainparser`.

.. module:: parsing
    :synopsis: Parsing logic for RepoBee's primary parser.

.. moduleauthor:: Simon Larsén
"""
import argparse
import logging
import os
import pathlib
import re
import sys
import enum
from typing import Iterable, Optional, List, Tuple, Generator

import daiquiri
import repobee_plug as plug

import _repobee
from _repobee import util, exception, constants
from _repobee.cli.mainparser import (
    create_parser,
    SHOW_CONFIG_PARSER,
    VERIFY_PARSER,
    CLONE_PARSER,
    SETUP_PARSER,
    DEPRECATED_PARSERS,
    LOGGER,
)


class _ArgsProcessing(enum.Enum):
    """Enum for selecting the type of processing for args."""

    NONE = "none"
    CORE = "core"
    EXT = "ext"


def handle_args(
    sys_args: Iterable[str],
    show_all_opts: bool = False,
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
) -> Tuple[argparse.Namespace, Optional[plug.API]]:
    """Parse and process command line arguments and instantiate the platform
    API (if it's needed).


    Args:
        sys_args: Raw command line arguments for the primary parser.
        show_all_opts: If False, help sections for options that have
            configured defaults are suppressed. Otherwise, all options are
            shown.
        ext_commands: An optional list of extension commands.

    Returns:
        A tuple of a namespace with parsed and processed arguments, and an
        instance of the platform API if it is required for the command.
    """
    args, processing = _parse_args(sys_args, show_all_opts, ext_commands)
    if processing == _ArgsProcessing.CORE:
        processed_args, api = _process_args(args, ext_commands)
        _handle_task_parsing(processed_args)
        return processed_args, api
    elif processing == _ArgsProcessing.EXT:
        processed_args, api = _process_ext_args(args, ext_commands)
        return processed_args, api
    return args, None


def _parse_args(
    sys_args: Iterable[str],
    show_all_opts: bool = False,
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
) -> Tuple[argparse.Namespace, _ArgsProcessing]:
    """Parse the command line arguments with some light processing. Any
    processing that requires external resources (such as a network connection)
    must be performed by the :py:func:`_process_args` function.

    Args:
        sys_args: A list of command line arguments.
        show_all_opts: If False, CLI arguments that are configure in the
            configuration file are not shown in help menus.
        ext_commands: A list of extension commands.

    Returns:
        A namespace of parsed arpuments and a boolean that specifies whether or
        not further processing is required.
    """
    parser = create_parser(show_all_opts, ext_commands)
    args = parser.parse_args(_handle_deprecation(sys_args))

    ext_cmd = _resolve_extension_command(args.subparser, ext_commands)
    if ext_cmd:
        return args, _ArgsProcessing.EXT

    if "base_url" in args:
        _validate_tls_url(args.base_url)

    args_dict = vars(args)
    args_dict["students"] = _extract_groups(args)
    args_dict["issue"] = (
        util.read_issue(args.issue) if "issue" in args and args.issue else None
    )
    args_dict.setdefault("master_org_name", None)
    args_dict.setdefault("title_regex", None)
    args_dict.setdefault("state", None)
    args_dict.setdefault("show_body", None)
    args_dict.setdefault("author", None)
    args_dict.setdefault("num_reviews", None)
    args_dict.setdefault("user", None)

    requires_processing = _resolve_requires_processing(args.subparser)
    return argparse.Namespace(**args_dict), requires_processing


def _resolve_extension_command(
    subparser, ext_commands
) -> Optional[plug.ExtensionCommand]:
    ext_command_names = [cmd.name for cmd in ext_commands or []]
    if subparser in ext_command_names:
        return ext_commands[ext_command_names.index(subparser)]
    return None


def _resolve_requires_processing(subparser) -> _ArgsProcessing:
    """Figure out if further processing of the parsed args is required.
    This is primarily decided on whether or not the platform API is required,
    as that implies further processing.
    """
    if subparser in [VERIFY_PARSER, SHOW_CONFIG_PARSER]:
        return _ArgsProcessing.NONE
    return _ArgsProcessing.CORE


def _process_args(
    args: argparse.Namespace,
    ext_commands: Optional[List[plug.ExtensionCommand]] = None,
) -> Tuple[argparse.Namespace, plug.API]:
    """Process parsed command line arguments.

    Args:
    """
    api = _connect_to_api(args.base_url, args.token, args.org_name, args.user)

    master_org_name = args.org_name
    if "master_org_name" in args and args.master_org_name is not None:
        master_org_name = args.master_org_name

    repos = master_names = master_urls = None
    if "discover_repos" in args and args.discover_repos:
        repos = api.discover_repos(args.students)
    elif "master_repo_names" in args:
        master_names = args.master_repo_names
        master_urls = _repo_names_to_urls(master_names, master_org_name, api)
        repos = _repo_tuple_generator(master_names, args.students, api)
        assert master_urls and master_names

    args_dict = vars(args)
    args_dict["master_repo_urls"] = master_urls
    args_dict["master_repo_names"] = master_names
    args_dict["repos"] = repos
    # marker for functionality that relies on fully processed args
    args_dict["_repobee_processed"] = True

    return argparse.Namespace(**args_dict), api


def _repo_tuple_generator(
    master_repo_names: List[str], teams: List[plug.Team], api: plug.API
) -> Generator[plug.Repo, None, None]:
    for master_repo_name in master_repo_names:
        for team in teams:
            url, *_ = api.get_repo_urls([master_repo_name], teams=[team])
            name = plug.generate_repo_name(team, master_repo_name)
            yield plug.Repo(name=name, url=url, private=True, description="")


def _handle_task_parsing(args: argparse.Namespace) -> None:
    """Call hooks that allows Tasks to parse command line arguments. Must be
    called with fully processed args.
    """
    if args.subparser not in [CLONE_PARSER, SETUP_PARSER]:
        return

    assert args._repobee_processed
    if args.subparser == CLONE_PARSER:
        plug.manager.hook.parse_args(args=args)
        for task in plug.manager.hook.clone_task():
            util.call_if_defined(task.handle_args, args)
    elif args.subparser == SETUP_PARSER:
        for task in plug.manager.hook.setup_task():
            util.call_if_defined(task.handle_args, args)


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
                parser_name,
                deprecation.remove_by_version,
                deprecation.replacement,
            )
        )
        return [deprecation.replacement] + sys_args[1:]

    return list(sys_args)


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


def _process_ext_args(
    args: argparse.Namespace, ext_commands: List[plug.ExtensionCommand]
) -> Tuple[argparse.Namespace, Optional[plug.API]]:
    ext_cmd = _resolve_extension_command(args.subparser, ext_commands)
    assert ext_cmd

    api = None
    if ext_cmd.requires_api:
        _validate_tls_url(args.base_url)
        api = _connect_to_api(
            args.base_url,
            args.token,
            args.org_name,
            args.user if "user" in args else None,
        )

    args_dict = vars(args)
    req_parsers = ext_cmd.requires_base_parsers or []
    bp = plug.BaseParser
    if bp.STUDENTS in req_parsers:
        args_dict["students"] = _extract_groups(args)
    if bp.REPO_DISCOVERY in req_parsers:
        args_dict["repos"] = api.discover_repos(args_dict["students"])

    return argparse.Namespace(**args_dict), api


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


def setup_logging() -> None:
    """Setup logging by creating the required log directory and setting up
    the logger.
    """
    try:
        os.makedirs(str(constants.LOG_DIR), exist_ok=True)
    except Exception as exc:
        raise exception.FileError(
            "can't create log directory at {}".format(constants.LOG_DIR)
        ) from exc

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
                filename=str(
                    constants.LOG_DIR
                    / "{}.log".format(_repobee._external_package_name)
                ),
                formatter=daiquiri.formatter.ColorFormatter(
                    fmt="%(asctime)s [PID %(process)d] [%(levelname)s] "
                    "%(name)s -> %(message)s"
                ),
            ),
        ),
    )

    _filter_tokens()
