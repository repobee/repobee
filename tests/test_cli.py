import os
import pathlib
from unittest.mock import MagicMock
from unittest import mock
import pytest

import repomate
from repomate import cli
from repomate import tuples
from repomate import exception
from repomate.tuples import Team

import constants
import functions

USER = constants.USER
ORG_NAME = constants.ORG_NAME
GITHUB_BASE_URL = constants.GITHUB_BASE_URL
STUDENTS = constants.STUDENTS
ISSUE_PATH = constants.ISSUE_PATH
ISSUE = constants.ISSUE
generate_repo_url = functions.generate_repo_url
MASTER_ORG_NAME = constants.MASTER_ORG_NAME
TOKEN = constants.TOKEN

REPO_NAMES = ("week-1", "week-2", "week-3")
REPO_URLS = tuple(map(lambda rn: generate_repo_url(rn, ORG_NAME), REPO_NAMES))

BASE_ARGS = ["-g", GITHUB_BASE_URL, "-o", ORG_NAME]
BASE_PUSH_ARGS = ["-u", USER, "-mn", *REPO_NAMES]
COMPLETE_PUSH_ARGS = [*BASE_ARGS, *BASE_PUSH_ARGS]

# parsed args without subparser
VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    github_base_url=GITHUB_BASE_URL,
    user=USER,
    master_repo_urls=REPO_URLS,
    master_repo_names=REPO_NAMES,
    students=STUDENTS,
    issue=ISSUE,
    title_regex="some regex",
    traceback=False,
    state="open",
    show_body=True,
    author=None,
    token=TOKEN,
)


@pytest.fixture(autouse=True)
def api_instance_mock(mocker):
    instance_mock = MagicMock(spec=repomate.github_api.GitHubAPI)
    instance_mock.get_repo_urls.side_effect = lambda repo_names, org_name: [
        generate_repo_url(rn, org_name) for rn in repo_names
    ]
    instance_mock.ensure_teams_and_members.side_effect = lambda team_dict: [
        Team(name, members, id=0) for name, members in team_dict.items()
    ]
    return instance_mock


@pytest.fixture(autouse=True)
def api_class_mock(mocker, api_instance_mock):
    class_mock = mocker.patch("repomate.github_api.GitHubAPI", autospec=True)
    class_mock.return_value = api_instance_mock
    return class_mock


@pytest.fixture
def command_mock(mocker):
    return mocker.patch("repomate.cli.command", autospec=True)


@pytest.fixture
def read_issue_mock(mocker):
    """Mock util.read_issue that only accepts ISSUE_PATH as a valid file."""

    def read_issue(path):
        # note that this assumes that strings are passed, and not pathlib.Path
        # works just as well for mock testing
        if path != ISSUE_PATH:
            raise ValueError("not a file")
        return ISSUE

    return mocker.patch(
        "repomate.util.read_issue", autospec=True, side_effect=read_issue
    )


@pytest.fixture
def git_mock(mocker):
    return mocker.patch("repomate.git", autospec=True)


@pytest.fixture(scope="function", params=cli.PARSER_NAMES)
def parsed_args_all_subparsers(request):
    """Parametrized fixture which returns a tuples.Args for each of the
    subparsers. These arguments are valid for all subparsers, even though
    many will only use some of the arguments.
    """
    return tuples.Args(subparser=request.param, **VALID_PARSED_ARGS)


@pytest.fixture(
    scope="function",
    params=[
        exception.PushFailedError("some message", 128, b"error", "someurl"),
        exception.CloneFailedError("some message", 128, b"error", "someurl"),
        exception.GitError("some message", 128, b"error"),
        exception.APIError("some message"),
    ],
)
def command_all_raise_mock(command_mock, api_class_mock, request):
    """Mock of repomate.command where all functions raise expected exceptions
    (i.e. those caught in _sys_exit_on_expected_error)
    """

    def raise_(*args, **kwargs):
        raise request.param

    command_mock.setup_student_repos.side_effect = raise_
    command_mock.update_student_repos.side_effect = raise_
    command_mock.open_issue.side_effect = raise_
    command_mock.close_issue.side_effect = raise_
    command_mock.migrate_repos.side_effect = raise_
    command_mock.clone_repos.side_effect = raise_
    command_mock.check_peer_review_progress.side_effect = raise_
    command_mock.show_config.side_effect = raise_
    command_mock.purge_review_teams.side_effect = raise_
    command_mock.assign_peer_reviews.side_effect = raise_
    command_mock.list_issues.side_effect = raise_
    api_class_mock.verify_settings.side_effect = raise_
    return command_mock


class TestDispatchCommand:
    """Test the handling of parsed arguments."""

    def test_raises_on_invalid_subparser_value(self, api_instance_mock):
        parser = "DOES_NOT_EXIST"
        args = tuples.Args(parser, **VALID_PARSED_ARGS)

        with pytest.raises(exception.ParseError) as exc_info:
            cli.dispatch_command(args, api_instance_mock)
        assert "Illegal value for subparser: {}".format(parser) in str(
            exc_info
        )

    def test_no_crash_on_valid_args(
        self, parsed_args_all_subparsers, api_instance_mock, command_mock
    ):
        """Test that valid arguments does not result in crash. Only validates
        that there are no crashes, does not validate any other behavior!"""
        cli.dispatch_command(parsed_args_all_subparsers, api_instance_mock)

    def test_expected_exception_results_in_system_exit(
        self,
        parsed_args_all_subparsers,
        api_instance_mock,
        command_all_raise_mock,
    ):
        """Test that any of the expected exceptions results in SystemExit."""
        with pytest.raises(SystemExit):
            cli.dispatch_command(parsed_args_all_subparsers, api_instance_mock)

    def test_setup_student_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.SETUP_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.setup_student_repos.assert_called_once_with(
            args.master_repo_urls, args.students, args.user, api_instance_mock
        )

    def test_update_student_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.UPDATE_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.update_student_repos.assert_called_once_with(
            args.master_repo_urls,
            args.students,
            args.user,
            api_instance_mock,
            issue=args.issue,
        )

    def test_open_issue_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.OPEN_ISSUE_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.open_issue.assert_called_once_with(
            args.issue,
            args.master_repo_names,
            args.students,
            api_instance_mock,
        )

    def test_close_issue_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.CLOSE_ISSUE_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.close_issue.assert_called_once_with(
            args.title_regex,
            args.master_repo_names,
            args.students,
            api_instance_mock,
        )

    def test_migrate_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.MIGRATE_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.migrate_repos.assert_called_once_with(
            args.master_repo_urls, args.user, api_instance_mock
        )

    def test_clone_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = tuples.Args(cli.CLONE_PARSER, **VALID_PARSED_ARGS)

        cli.dispatch_command(args, api_instance_mock)

        command_mock.clone_repos.assert_called_once_with(
            args.master_repo_names, args.students, api_instance_mock
        )

    def test_verify_settings_called_with_correct_args(self, api_class_mock):
        # regular mockaing is broken for static methods, it seems, produces
        # non-callable so using monkeypatch instead
        args = tuples.Args(
            cli.VERIFY_PARSER,
            user=USER,
            github_base_url=GITHUB_BASE_URL,
            token=TOKEN,
            org_name=ORG_NAME,
        )

        cli.dispatch_command(args, None)

        api_class_mock.verify_settings.assert_called_once_with(
            args.user, args.org_name, args.github_base_url, TOKEN, None
        )

    def test_verify_settings_called_with_master_org_name(self, api_class_mock):
        args = tuples.Args(
            cli.VERIFY_PARSER,
            user=USER,
            github_base_url=GITHUB_BASE_URL,
            org_name=ORG_NAME,
            token=TOKEN,
            master_org_name=MASTER_ORG_NAME,
        )

        cli.dispatch_command(args, None)

        api_class_mock.verify_settings.assert_called_once_with(
            args.user,
            args.org_name,
            args.github_base_url,
            TOKEN,
            MASTER_ORG_NAME,
        )


class TestBaseParsing:
    """Test the basic functionality of parsing."""

    def test_raises_on_invalid_org(self, api_class_mock, students_file):
        """Test that an appropriate error is raised when the organization is
        not found.
        """

        def raise_(*args, **kwargs):
            raise exception.NotFoundError("Couldn't find the organization.")

        api_class_mock.side_effect = raise_

        with pytest.raises(exception.NotFoundError) as exc_info:
            cli.parse_args(
                [
                    cli.SETUP_PARSER,
                    *COMPLETE_PUSH_ARGS,
                    "-sf",
                    str(students_file),
                ]
            )

        assert "organization {} could not be found".format(ORG_NAME) in str(
            exc_info
        )

    def test_raises_on_bad_credentials(self, api_class_mock, students_file):
        def raise_(*args, **kwargs):
            raise exception.BadCredentials("bad credentials")

        api_class_mock.side_effect = raise_

        with pytest.raises(exception.BadCredentials) as exc_info:
            cli.parse_args(
                [
                    cli.SETUP_PARSER,
                    *COMPLETE_PUSH_ARGS,
                    "-sf",
                    str(students_file),
                ]
            )

        assert "bad credentials" in str(exc_info)

    def test_raises_on_invalid_base_url(self, api_class_mock, students_file):
        def raise_(*args, **kwargs):
            raise exception.ServiceNotFoundError(
                "GitHub service could not be found, check the url"
            )

        api_class_mock.side_effect = raise_

        with pytest.raises(exception.ServiceNotFoundError) as exc_info:
            cli.parse_args(
                [
                    cli.SETUP_PARSER,
                    *COMPLETE_PUSH_ARGS,
                    "-sf",
                    str(students_file),
                ]
            )

        assert "GitHub service could not be found, check the url" in str(
            exc_info
        )

    @pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
    def test_master_org_overrides_target_org_for_master_repos(
        self, command_mock, api_instance_mock, students_file, parser
    ):
        parsed_args, _ = cli.parse_args(
            [
                cli.SETUP_PARSER,
                *COMPLETE_PUSH_ARGS,
                "-sf",
                str(students_file),
                "-mo",
                MASTER_ORG_NAME,
            ]
        )

        assert all(
            [
                "/" + MASTER_ORG_NAME + "/" in url
                for url in parsed_args.master_repo_urls
            ]
        )

    @pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
    def test_master_org_name_defaults_to_org_name(
        self, api_instance_mock, students_file, parser
    ):
        parsed_args, _ = cli.parse_args(
            [parser, *COMPLETE_PUSH_ARGS, "-sf", str(students_file)]
        )

        assert all(
            [
                "/" + ORG_NAME + "/" in url
                for url in parsed_args.master_repo_urls
            ]
        )

    @pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
    def test_token_env_variable_picked_up(
        self, api_instance_mock, students_file, parser
    ):
        parsed_args, _ = cli.parse_args(
            [parser, *COMPLETE_PUSH_ARGS, "-sf", str(students_file)]
        )

        assert parsed_args.token == TOKEN

    @pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
    def test_token_cli_arg_picked_up(
        self, mocker, api_instance_mock, students_file, parser
    ):
        mocker.patch("os.getenv", return_value="")
        token = "supersecretothertoken"
        parsed_args, _ = cli.parse_args(
            [
                parser,
                *COMPLETE_PUSH_ARGS,
                "-sf",
                str(students_file),
                "-t",
                token,
            ]
        )

        assert parsed_args.token == token

    @pytest.mark.parametrize(
        "url",
        [
            GITHUB_BASE_URL.replace("https://", non_tls_protocol)
            for non_tls_protocol in ("http://", "ftp://", "")
        ],
    )
    def test_raises_on_non_tls_api_url(
        self, api_instance_mock, students_file, url
    ):
        """Test that a non https url causes parse-args to raise. Sending the token
        over an unencrypted connection would be a security risk, so https is
        required.
        """
        sys_args = [
            cli.SETUP_PARSER,
            "-o",
            ORG_NAME,
            "-g",
            url,
            *BASE_PUSH_ARGS,
            "-sf",
            str(students_file),
        ]

        with pytest.raises(exception.ParseError) as exc_info:
            cli.parse_args(sys_args)

        assert "unsupported protocol in {}".format(url) in str(exc_info)


class TestStudentParsing:
    """Tests for the parsers that use the `--students` and `--students-file`
    arguments.

    Currently these are:

        cli.SETUP_PARSER
        cli.UPDATE_PARSER
        cli.OPEN_ISSUE_PARSER
        cli.CLOSE_ISSUE_PARSER
    """

    STUDENT_PARSING_PARAMS = (
        "parser, extra_args",
        [
            (cli.SETUP_PARSER, BASE_PUSH_ARGS),
            (cli.UPDATE_PARSER, BASE_PUSH_ARGS),
            (cli.CLOSE_ISSUE_PARSER, ["-mn", *REPO_NAMES, "-r", "some-regex"]),
            (cli.OPEN_ISSUE_PARSER, ["-mn", *REPO_NAMES, "-i", ISSUE_PATH]),
        ],
    )
    STUDENT_PARSING_IDS = [
        "|".join([str(val) for val in line])
        for line in STUDENT_PARSING_PARAMS[1]
    ]

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_raises_if_students_file_is_not_a_file(self, parser, extra_args):
        not_a_file = "this-is-not-a-file"
        sys_args = [parser, *BASE_ARGS, "-sf", not_a_file, *extra_args]

        with pytest.raises(exception.FileError) as exc_info:
            cli.parse_args(sys_args)

        assert not_a_file in str(exc_info)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_listing_students(
        self, read_issue_mock, parser, extra_args
    ):
        """Test that the different subparsers parse arguments corectly when
        students are listed directly on the command line.
        """
        sys_args = [parser, *BASE_ARGS, "-s", *STUDENTS, *extra_args]

        parsed_args, _ = cli.parse_args(sys_args)

        assert parsed_args.students == list(STUDENTS)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_student_file(
        self, students_file, read_issue_mock, parser, extra_args
    ):
        """Test that the different subparsers read students correctly from
        file.
        """
        sys_args = [parser, *BASE_ARGS, "-sf", str(students_file), *extra_args]

        parsed_args, _ = cli.parse_args(sys_args)

        assert parsed_args.students == list(STUDENTS)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_student_parsers_raise_on_empty_student_file(
        self, read_issue_mock, empty_students_file, parser, extra_args
    ):
        """Test that an error is raised if the student file is empty."""
        sys_args = [
            parser,
            *BASE_ARGS,
            "-sf",
            str(empty_students_file),
            *extra_args,
        ]

        with pytest.raises(exception.FileError) as exc_info:
            cli.parse_args(sys_args)

        assert "is empty" in str(exc_info)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parsers_raise_if_both_file_and_listing(
        read_issue_mock, students_file, parser, extra_args
    ):
        """Test that the student subparsers raise if students are both listed
        on the CLI, and a file is specified.
        """
        sys_args = [
            parser,
            *BASE_ARGS,
            "-sf",
            str(students_file),
            "-s",
            *STUDENTS,
            *extra_args,
        ]

        with pytest.raises(SystemExit):
            cli.parse_args(sys_args)


def assert_base_push_args(parsed_args, api):
    """Assert that the parsed arguments are consistend with the
    BASE_PUSH_ARGS.
    """
    assert parsed_args.org_name == ORG_NAME
    assert parsed_args.github_base_url == GITHUB_BASE_URL
    assert parsed_args.user == USER
    assert parsed_args.master_repo_names == list(REPO_NAMES)
    assert parsed_args.master_repo_urls == [
        generate_repo_url(rn, ORG_NAME) for rn in REPO_NAMES
    ]
    api.assert_called_once_with(GITHUB_BASE_URL, TOKEN, ORG_NAME)


def assert_config_args(parser, parsed_args):
    """Asserts that the configured arguments are correct."""
    assert parsed_args.github_base_url == GITHUB_BASE_URL
    assert parsed_args.students == list(STUDENTS)
    assert parsed_args.org_name == ORG_NAME

    if parser in [cli.SETUP_PARSER, cli.UPDATE_PARSER]:
        assert parsed_args.user == USER


class TestConfig:
    """Tests that the configuration works properly."""

    @pytest.mark.parametrize(
        "parser, extra_args",
        [
            (cli.SETUP_PARSER, ["-mn", *REPO_NAMES]),
            (cli.UPDATE_PARSER, ["-mn", *REPO_NAMES]),
            (cli.OPEN_ISSUE_PARSER, ["-mn", *REPO_NAMES, "-i", ISSUE_PATH]),
        ],
    )
    def test_full_config(
        self, config_mock, read_issue_mock, parser, extra_args
    ):
        """Test that a fully configured file works. This means that
        github_base_url, org_name, user and student list are all
        preconfigured.
        """
        sys_args = [parser, *extra_args]

        parsed_args, _ = cli.parse_args(sys_args)
        assert_config_args(parser, parsed_args)

    # TODO test that not having github_base_url, org_name, user or
    # students_file in the config makes them required!

    def test_missing_option_is_required(self, config_missing_option):
        """Test that a config that is missing one option (that is not
        specified on the command line) causes a SystemExit on parsing.
        """
        # -mo is not required
        if config_missing_option == "-mo":
            return

        sys_args = [cli.SETUP_PARSER, "-mn", *REPO_NAMES]

        with pytest.raises(SystemExit):
            parsed_args, _ = cli.parse_args(sys_args)
        # TODO actually verify that the SystemExit came from the parsing!

    def test_missing_option_can_be_specified(
        self, config_missing_option, mocker, students_file
    ):
        """Test that a missing config option can be specified on the command
        line. Does not assert that the options are parsed correctly, only that
        there's no crash.
        """
        if config_missing_option == "-sf":  # must be file
            missing_arg = str(students_file)
        elif config_missing_option == "-g":  # must be https url
            missing_arg = GITHUB_BASE_URL
        else:
            missing_arg = "whatever"

        sys_args = [
            cli.SETUP_PARSER,
            "-mn",
            *REPO_NAMES,
            config_missing_option,
            missing_arg,
        ]

        # only asserts that there is no crash
        cli.parse_args(sys_args)


@pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
class TestSetupAndUpdateParsers:
    """Tests that are in common for SETUP_PARSER and UPDATE_PARSER."""

    def test_happy_path(self, api_class_mock, parser):
        """Tests standard operation of the parsers."""
        sys_args = [parser, *COMPLETE_PUSH_ARGS, "-s", *STUDENTS]

        parsed_args, _ = cli.parse_args(sys_args)

        assert_base_push_args(parsed_args, api_class_mock)

    def test_finds_local_repo(self, mocker, api_instance_mock, parser):
        """Tests that the parsers pick up local repos when they are not
        found in the organization.
        """
        local_repo = REPO_NAMES[-1]
        mocker.patch(
            "repomate.util.is_git_repo",
            side_effect=lambda path: path.endswith(local_repo),
        )
        expected_urls = [
            generate_repo_url(name, ORG_NAME)
            for name in REPO_NAMES
            if name != local_repo
        ]
        expected_uris = [pathlib.Path(os.path.abspath(local_repo)).as_uri()]
        expected = expected_urls + expected_uris
        api_instance_mock.get_repo_urls.side_effect = lambda repo_names, _: [
            generate_repo_url(name, ORG_NAME) for name in repo_names
        ]

        sys_args = [parser, *COMPLETE_PUSH_ARGS, "-s", *STUDENTS]

        parsed_args, _ = cli.parse_args(sys_args)

        assert sorted(parsed_args.master_repo_urls) == sorted(expected)


class TestMigrateParser:
    """Tests for MIGRATE_PARSER."""

    NAMES = ["some-repo", "other-repo"]
    URLS = [
        "https://someurl.org/{}".format(NAMES[0]),
        "https://otherurl.com/{}".format(NAMES[1]),
    ]
    LOCAL_URIS = [
        pathlib.Path(os.path.abspath(name)).as_uri() for name in NAMES
    ]

    @pytest.fixture(autouse=True)
    def is_git_repo_mock(self, mocker):
        return mocker.patch(
            "repomate.util.is_git_repo", autospec=True, return_value=True
        )

    def assert_migrate_args(self, parsed_args, *, uses_urls: bool) -> bool:
        assert parsed_args.user == USER
        assert parsed_args.org_name == ORG_NAME
        assert parsed_args.github_base_url == GITHUB_BASE_URL
        assert parsed_args.master_repo_names == self.NAMES
        if uses_urls:
            assert parsed_args.master_repo_urls == self.URLS
        else:
            assert parsed_args.master_repo_urls == self.LOCAL_URIS

    def test_handles_urls_only(self):
        """Test that the migrate parser handles master repo urls only
        correctly.
        """
        sys_args = [
            cli.MIGRATE_PARSER,
            *BASE_ARGS,
            "-u",
            USER,
            "-mu",
            *self.URLS,
        ]

        parsed_args, _ = cli.parse_args(sys_args)

        self.assert_migrate_args(parsed_args, uses_urls=True)

    def test_handles_names_only(self):
        """Test that the migrate parser handles master repo names only
        correctly.
        """
        sys_args = [
            cli.MIGRATE_PARSER,
            *BASE_ARGS,
            "-u",
            USER,
            "-mn",
            *self.NAMES,
        ]

        parsed_args, _ = cli.parse_args(sys_args)

        self.assert_migrate_args(parsed_args, uses_urls=False)


class TestVerifyParser:
    """Tests for the VERIFY_PARSER."""

    def test_happy_path(self):
        sys_args = [cli.VERIFY_PARSER, *BASE_ARGS, "-u", USER]

        args, _ = cli.parse_args(sys_args)

        assert args.subparser == cli.VERIFY_PARSER
        assert args.org_name == ORG_NAME
        assert args.github_base_url == GITHUB_BASE_URL
        assert args.user == USER


class TestCloneParser:
    """Tests for the CLONE_PARSER."""

    def test_happy_path(self, students_file, plugin_manager_mock):
        sys_args = [
            cli.CLONE_PARSER,
            *BASE_ARGS,
            "-mn",
            *REPO_NAMES,
            "-sf",
            str(students_file),
        ]

        args, _ = cli.parse_args(sys_args)

        assert args.subparser == cli.CLONE_PARSER
        assert args.org_name == ORG_NAME
        assert args.github_base_url == GITHUB_BASE_URL
        assert args.students == list(STUDENTS)
        # TODO assert with actual value
        plugin_manager_mock.hook.clone_parser_hook.assert_called_once_with(
            clone_parser=mock.ANY
        )
        plugin_manager_mock.hook.parse_args.assert_called_once_with(
            args=mock.ANY
        )

    STUDENTS_STRING = " ".join(STUDENTS)

    # def test_no_plugins_option_drops_plugins()

    @pytest.mark.parametrize(
        "parser, extra_args",
        [
            (
                cli.SETUP_PARSER,
                ["-u", USER, "-s", STUDENTS_STRING, "-mn", *REPO_NAMES],
            ),
            (
                cli.UPDATE_PARSER,
                ["-u", USER, "-s", STUDENTS_STRING, "-mn", *REPO_NAMES],
            ),
            (
                cli.OPEN_ISSUE_PARSER,
                ["-s", STUDENTS_STRING, "-mn", *REPO_NAMES, "-i", ISSUE_PATH],
            ),
            (
                cli.CLOSE_ISSUE_PARSER,
                [
                    "-s",
                    STUDENTS_STRING,
                    "-mn",
                    *REPO_NAMES,
                    "-r",
                    "some-regex",
                ],
            ),
            (cli.VERIFY_PARSER, ["-u", USER]),
            (cli.MIGRATE_PARSER, ["-u", USER, "-mn", *REPO_NAMES]),
        ],
    )
    def test_no_other_parser_gets_parse_hook(
        self, parser, extra_args, plugin_manager_mock, read_issue_mock
    ):
        sys_args = [parser, *BASE_ARGS, *extra_args]

        args, _ = cli.parse_args(sys_args)

        plugin_manager_mock.hook.clone_parser_hook.assert_called_once_with(
            clone_parser=mock.ANY
        )
        assert not plugin_manager_mock.hook.parse_args.called


class TestCommandDeprecation:
    """Tests for deprecated commands, making sure they still work and have the
    same effect as the replacement commands.

    The semantics of deprecation of a command is that the old command should
    still work, but it should be parsed to the new command.
    """

    @pytest.mark.parametrize(
        "deprecated_parser, current_parser, sys_args",
        [
            (
                cli.ASSIGN_REVIEWS_PARSER_OLD,
                cli.ASSIGN_REVIEWS_PARSER,
                [
                    *BASE_ARGS,
                    "-mn",
                    "week-10",
                    "-i",
                    ISSUE_PATH,
                    "-s",
                    *STUDENTS,
                    "-n",
                    "3",
                ],
            ),
            (
                cli.PURGE_REVIEW_TEAMS_PARSER_OLD,
                cli.PURGE_REVIEW_TEAMS_PARSER,
                [*BASE_ARGS, "-mn", "week-10", "-s", *STUDENTS],
            ),
            (
                cli.CHECK_REVIEW_PROGRESS_PARSER_OLD,
                cli.CHECK_REVIEW_PROGRESS_PARSER,
                [
                    *BASE_ARGS,
                    "-mn",
                    "week-10",
                    "-r",
                    "someregex",
                    "-n",
                    "3",
                    "-s",
                    *STUDENTS,
                ],
            ),
        ],
    )
    def test_deprecated_commands_parsed_to_current_commands(
        self, deprecated_parser, current_parser, sys_args, read_issue_mock
    ):
        """Test that the deprecated commands are substituted for the current ones.

        Note that the ``read_issue_mock`` is necessary for the
        ``assign_reviews`` command only (at this time).
        """
        old_sys_args = [deprecated_parser] + sys_args
        new_sys_args = [current_parser] + sys_args

        old_parsed_args, old_api = cli.parse_args(old_sys_args)
        new_parsed_args, new_api = cli.parse_args(new_sys_args)

        assert old_parsed_args.subparser == current_parser
        assert old_parsed_args == new_parsed_args
        assert old_api == new_api
