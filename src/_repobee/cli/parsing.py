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
from typing import Iterable, Optional, List, Tuple

import argcomplete  # type: ignore
import daiquiri  # type: ignore
import repobee_plug as plug
from repobee_plug.cli import categorization

import _repobee
import _repobee.cli.mainparser
import _repobee.cli.preparser
from _repobee import fileutil, exception, constants, cli, git

from _repobee.command import progresswrappers


class _ArgsProcessing(enum.Enum):
    """Enum for selecting the type of processing for args."""

    NONE = "none"
    CORE = "core"
    EXT = "ext"


def handle_args(
    sys_args: Iterable[str], config: plug.Config
) -> Tuple[argparse.Namespace, Optional[plug.PlatformAPI]]:
    """Parse and process command line arguments and instantiate the platform
    API (if it's needed).


    Args:
        sys_args: Raw command line arguments for the primary parser.
        config: RepoBee's configuration.
    Returns:
        A tuple of a namespace with parsed and processed arguments, and an
        instance of the platform API if it is required for the command.
    """
    args, processing = _parse_args(sys_args, config)
    plug.manager.hook.handle_parsed_args(args=args)

    if processing == _ArgsProcessing.CORE:
        return _process_args(args)
    elif processing == _ArgsProcessing.EXT:
        return _process_ext_args(args)
    return args, None


def _parse_args(
    sys_args: Iterable[str], config: plug.Config
) -> Tuple[argparse.Namespace, _ArgsProcessing]:
    """Parse the command line arguments with some light processing. Any
    processing that requires external resources (such as a network connection)
    must be performed by the :py:func:`_process_args` function.

    Args:
        sys_args: A list of command line arguments.
        config: RepoBee's configuration.
    Returns:
        A namespace of parsed arpuments and a boolean that specifies whether or
        not further processing is required.
    """
    parser = cli.mainparser.create_parser(config)
    argcomplete.autocomplete(parser)

    args = parser.parse_args(_handle_deprecation(sys_args))
    cli.preparser.clean_arguments(args)

    if "_extension_command" in args and not getattr(
        args._extension_command, "_is_core_command", False
    ):
        return args, _ArgsProcessing.EXT

    if "base_url" in args:
        _validate_tls_url(args.base_url)

    args_dict = vars(args)
    args_dict["students"] = _extract_groups(args)
    args_dict["issue"] = (
        fileutil.read_issue_from_file(args.issue)
        if "issue" in args and args.issue
        else None
    )
    args_dict.setdefault("template_org_name", None)
    args_dict.setdefault("title_regex", None)
    args_dict.setdefault("state", None)
    args_dict.setdefault("show_body", None)
    args_dict.setdefault("author", None)
    args_dict.setdefault("num_reviews", None)
    args_dict.setdefault("user", None)
    args_dict["action"] = (
        args.action
        if isinstance(args.action, categorization.Action)
        else plug.cli.CoreCommand(args.category)[args.action]
    )
    args_dict["category"] = (
        args.category
        if isinstance(args.category, categorization.Category)
        else plug.cli.CoreCommand(args.category)
    )

    requires_processing = _resolve_requires_processing(args)
    return argparse.Namespace(**args_dict), requires_processing


def _resolve_requires_processing(args: argparse.Namespace) -> _ArgsProcessing:
    """Figure out if further processing of the parsed args is required.
    This is primarily decided on whether or not the platform API is required,
    as that implies further processing.
    """
    if args.action in [
        plug.cli.CoreCommand.config.verify,
        plug.cli.CoreCommand.config.show,
    ]:
        return _ArgsProcessing.NONE
    return _ArgsProcessing.CORE


def _process_args(
    args: argparse.Namespace,
) -> Tuple[argparse.Namespace, plug.PlatformAPI]:
    """Process parsed command line arguments.

    Args:
    """
    api = _connect_to_api(args.base_url, args.token, args.org_name, args.user)

    template_org_name = args.org_name
    if "template_org_name" in args and args.template_org_name is not None:
        template_org_name = args.template_org_name

    repos = master_names = master_urls = None
    if "discover_repos" in args and args.discover_repos:
        repos = _discover_repos(args.students, api)
    elif "assignments" in args:
        master_names = args.assignments
        remote_urls, local_uris = _repo_names_to_urls(
            master_names, template_org_name, api
        )

        if local_uris and not getattr(args, "allow_local_templates", True):
            locals_str = " ".join([f"'{uri}'" for uri in local_uris])
            raise exception.ParseError(
                f"found local templates in workdir: {locals_str}, "
                "use `--allow-local-templates` to allow locals or change "
                "directory to use remotes only"
            )

        master_urls = remote_urls + local_uris
        repos = _repo_tuple_generator(master_names, args.students, api)
        assert master_urls and master_names

    args_dict = vars(args)
    args_dict["template_repo_urls"] = master_urls
    args_dict["assignments"] = master_names
    args_dict["repos"] = repos
    # marker for functionality that relies on fully processed args
    args_dict["_repobee_processed"] = True

    return argparse.Namespace(**args_dict), api


def _discover_repos(
    student_teams: List[plug.StudentTeam], api: plug.PlatformAPI
) -> Iterable[plug.StudentRepo]:
    student_teams_dict = {t.name: t for t in student_teams}
    fetched_teams = progresswrappers.get_teams(
        student_teams, api, desc="Discovering team repos"
    )
    for team in fetched_teams:
        repos = api.get_team_repos(team)
        yield from (
            plug.StudentRepo(
                name=repo.name,
                url=repo.url,
                team=student_teams_dict[team.name],
            )
            for repo in repos
        )


def _repo_tuple_generator(
    assignment_names: List[str],
    teams: List[plug.StudentTeam],
    api: plug.PlatformAPI,
) -> Iterable[plug.StudentRepo]:
    for assignment_name in assignment_names:
        for team in teams:
            url, *_ = api.get_repo_urls(
                [assignment_name], team_names=[team.name]
            )
            name = plug.generate_repo_name(team, assignment_name)
            yield plug.StudentRepo(name=name, url=url, team=team)


def _validate_tls_url(url):
    """Url must use the https protocol."""
    if not url.startswith("https://"):
        raise exception.ParseError(
            f"unsupported protocol in {url}: "
            f"for security reasons, only https is supported"
        )


def _handle_deprecation(sys_args: Iterable[str]) -> List[str]:
    """If the first argument on the arglist is a deprecated command, replace it
    with the corresponding current command and issue a warning.

    Returns:
        The sys_args list with any deprecated command replaced with the current
        one.
    """
    # FIXME Deprecation needs to be re-implemented
    return list(sys_args)


def _extract_groups(args: argparse.Namespace) -> List[plug.StudentTeam]:
    """Extract groups from args namespace.`

    Args:
        args: A namespace object.

    Returns:
        a list of student usernames, or None of neither `students` or
        `students_file` is in the namespace.
    """
    if "students" in args and args.students:
        students = [plug.StudentTeam(members=[s]) for s in args.students]
    elif "students_file" in args and args.students_file:
        students_file = pathlib.Path(args.students_file).resolve()
        if not students_file.is_file():
            raise exception.FileError(f"'{students_file}' is not a file")
        if not students_file.stat().st_size:
            raise exception.FileError(f"'{students_file}' is empty")

        students = list(
            plug.manager.hook.parse_students_file(students_file=students_file)
        )
    else:
        students = []

    return students


def _connect_to_api(
    base_url: str, token: str, org_name: str, user: str
) -> plug.PlatformAPI:
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
    except plug.NotFoundError:
        # more informative message
        raise plug.NotFoundError(
            f"either organization {org_name} could not be found, "
            f"or the base url '{base_url}' is incorrect"
        )


def _repo_names_to_urls(
    repo_names: Iterable[str], org_name: str, api: plug.PlatformAPI
) -> Tuple[List[str], List[str]]:
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
        A tuple of lists with (non_local_urls, local_uris).
    Raises:
        ParseError: If local templates are found, but allow_local is False.
    """
    local = [
        name for name in repo_names if git.is_git_repo(os.path.abspath(name))
    ]

    non_local = [name for name in repo_names if name not in local]

    non_local_urls = api.get_repo_urls(non_local, org_name)
    local_uris = [
        pathlib.Path(os.path.abspath(repo_name)).as_uri()
        for repo_name in local
    ]
    return non_local_urls, local_uris


def _process_ext_args(
    args: argparse.Namespace,
) -> Tuple[argparse.Namespace, Optional[plug.PlatformAPI]]:
    ext_cmd = args._extension_command
    assert ext_cmd

    api = None
    if ext_cmd.__requires_api__():
        _validate_tls_url(args.base_url)
        api = _connect_to_api(
            args.base_url,
            args.token,
            args.org_name,
            args.user if "user" in args else None,
        )

    args_dict = vars(args)
    req_parsers = ext_cmd.__settings__.base_parsers or []
    bp = plug.BaseParser
    if bp.STUDENTS in req_parsers:
        args_dict["students"] = _extract_groups(args)
    if bp.REPO_DISCOVERY in req_parsers and args.discover_repos:
        assert api is not None
        args_dict["repos"] = _discover_repos(args_dict["students"], api)

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


def setup_logging(terminal_level: int = logging.WARNING) -> None:
    """Setup logging by creating the required log directory and setting up
    the logger.

    Args:
        terminal_level: The logging level to use for printing to stderr.
    """
    logfile = constants.LOG_DIR / f"{_repobee._external_package_name}.log"
    _ensure_size_less(logfile, max_size=constants.MAX_LOGFILE_SIZE)
    try:
        os.makedirs(str(constants.LOG_DIR), exist_ok=True)
    except Exception as exc:
        raise exception.FileError(
            f"can't create log directory at {constants.LOG_DIR}"
        ) from exc

    daiquiri.setup(
        level=logging.DEBUG,
        outputs=(
            daiquiri.output.Stream(
                sys.stderr,
                formatter=daiquiri.formatter.ColorFormatter(
                    fmt="%(color)s[%(levelname)s] %(message)s%(color_stop)s"
                ),
                level=terminal_level,
            ),
            daiquiri.output.File(
                filename=str(logfile),
                formatter=daiquiri.formatter.ColorFormatter(
                    fmt="%(asctime)s [PID %(process)d] [%(levelname)s] "
                    "%(name)s -> %(message)s"
                ),
                level=logging.DEBUG,
            ),
        ),
    )

    _filter_tokens()


def _ensure_size_less(path: pathlib.Path, max_size: int) -> None:
    if not path.exists():
        return
    file_size = path.stat().st_size
    if file_size >= max_size:
        target = file_size - max_size // 2
        with open(path, mode="rb") as f:
            cur = target
            f.seek(cur)
            while f.read(1) != b"\n" and cur < file_size:
                cur += 1
                f.seek(cur)

            with open(
                path.parent / (path.name + ".tmp"), mode="wb"
            ) as tmp_file:
                for line in f.readlines():
                    tmp_file.write(line)

        path.unlink()
        pathlib.Path(tmp_file.name).rename(path)
