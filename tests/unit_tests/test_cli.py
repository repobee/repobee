import os
import pathlib
import argparse
from unittest.mock import MagicMock
from unittest import mock

import pytest

import repobee_plug as plug

import _repobee
import _repobee.ext
import _repobee.ext.github
import _repobee.constants
import _repobee.plugin
from _repobee import cli
from _repobee import exception
from repobee_plug import apimeta
from _repobee import tuples

import constants
import functions

USER = constants.USER
ORG_NAME = constants.ORG_NAME
BASE_URL = constants.BASE_URL
STUDENTS = constants.STUDENTS
STUDENTS_STRING = " ".join([str(s) for s in STUDENTS])
ISSUE_PATH = constants.ISSUE_PATH
ISSUE = constants.ISSUE
generate_repo_url = functions.generate_repo_url
MASTER_ORG_NAME = constants.MASTER_ORG_NAME
TOKEN = constants.TOKEN

REPO_NAMES = ("week-1", "week-2", "week-3")
REPO_URLS = tuple(map(lambda rn: generate_repo_url(rn, ORG_NAME), REPO_NAMES))

BASE_ARGS = ["-u", USER, "--bu", BASE_URL, "-o", ORG_NAME, "-t", TOKEN]
BASE_PUSH_ARGS = ["--mn", *REPO_NAMES]
COMPLETE_PUSH_ARGS = [*BASE_ARGS, *BASE_PUSH_ARGS]

# parsed args without subparser
VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    master_org_name=MASTER_ORG_NAME,
    base_url=BASE_URL,
    user=USER,
    master_repo_urls=REPO_URLS,
    master_repo_names=REPO_NAMES,
    students=STUDENTS,
    issue=ISSUE,
    title_regex="some regex",
    traceback=False,
    state=apimeta.IssueState.OPEN,
    show_body=True,
    author=None,
    token=TOKEN,
    num_reviews=1,
)


@pytest.fixture(autouse=True)
def api_instance_mock(mocker):
    instance_mock = MagicMock(spec=_repobee.ext.github.GitHubAPI)
    instance_mock.get_repo_urls.side_effect = lambda repo_names, org_name: [
        generate_repo_url(rn, org_name) for rn in repo_names
    ]
    instance_mock.ensure_teams_and_members.side_effect = lambda team_dict: [
        apimeta.Team(name=name, members=members, id=0)
        for name, members in team_dict.items()
    ]
    return instance_mock


@pytest.fixture(autouse=True)
def api_class_mock(mocker, api_instance_mock):
    class_mock = mocker.patch("_repobee.ext.github.GitHubAPI", autospec=True)
    class_mock.return_value = api_instance_mock
    return class_mock


@pytest.fixture(autouse=True)
def load_default_plugins(api_instance_mock):
    """Load the default plugins after mocking the GitHubAPI."""
    loaded = _repobee.plugin.load_plugin_modules(
        [_repobee.constants.DEFAULT_PLUGIN]
    )
    _repobee.plugin.register_plugins(loaded)


@pytest.fixture
def no_plugins(load_default_plugins):
    """Unregister any registered plugins."""
    for plugin in plug.manager.get_plugins():
        plug.manager.unregister(plugin=plugin)


@pytest.fixture
def command_mock(mocker):
    return mocker.patch("_repobee.cli.command", autospec=True)


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
        "_repobee.util.read_issue", autospec=True, side_effect=read_issue
    )


@pytest.fixture
def git_mock(mocker):
    return mocker.patch("_repobee.git", autospec=True)


@pytest.fixture(scope="function", params=cli.PARSER_NAMES)
def parsed_args_all_subparsers(request):
    """Parametrized fixture which returns a namespace for each of the
    subparsers. These arguments are valid for all subparsers, even though
    many will only use some of the arguments.
    """
    return argparse.Namespace(subparser=request.param, **VALID_PARSED_ARGS)


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
    """Mock of _repobee.command where all functions raise expected exceptions
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
        args = argparse.Namespace(subparser=parser, **VALID_PARSED_ARGS)

        with pytest.raises(exception.ParseError) as exc_info:
            cli.dispatch_command(args, api_instance_mock)
        assert "Illegal value for subparser: {}".format(parser) in str(
            exc_info.value
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
        args = argparse.Namespace(
            subparser=cli.SETUP_PARSER, **VALID_PARSED_ARGS
        )

        cli.dispatch_command(args, api_instance_mock)

        command_mock.setup_student_repos.assert_called_once_with(
            args.master_repo_urls, args.students, api_instance_mock
        )

    def test_update_student_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = argparse.Namespace(
            subparser=cli.UPDATE_PARSER, **VALID_PARSED_ARGS
        )

        cli.dispatch_command(args, api_instance_mock)

        command_mock.update_student_repos.assert_called_once_with(
            args.master_repo_urls,
            args.students,
            api_instance_mock,
            issue=args.issue,
        )

    def test_open_issue_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = argparse.Namespace(
            subparser=cli.OPEN_ISSUE_PARSER, **VALID_PARSED_ARGS
        )

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
        args = argparse.Namespace(
            subparser=cli.CLOSE_ISSUE_PARSER, **VALID_PARSED_ARGS
        )

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
        args = argparse.Namespace(
            subparser=cli.MIGRATE_PARSER, **VALID_PARSED_ARGS
        )

        cli.dispatch_command(args, api_instance_mock)

        command_mock.migrate_repos.assert_called_once_with(
            args.master_repo_urls, api_instance_mock
        )

    def test_clone_repos_called_with_correct_args(
        self, command_mock, api_instance_mock
    ):
        args = argparse.Namespace(
            subparser=cli.CLONE_PARSER, **VALID_PARSED_ARGS
        )

        cli.dispatch_command(args, api_instance_mock)

        command_mock.clone_repos.assert_called_once_with(
            args.master_repo_names, args.students, api_instance_mock
        )

    def test_verify_settings_called_with_correct_args(self, api_class_mock):
        # regular mockaing is broken for static methods, it seems, produces
        # non-callable so using monkeypatch instead
        args = argparse.Namespace(
            subparser=cli.VERIFY_PARSER,
            user=USER,
            base_url=BASE_URL,
            token=TOKEN,
            org_name=ORG_NAME,
            master_org_name=None,
        )

        cli.dispatch_command(args, None)

        api_class_mock.verify_settings.assert_called_once_with(
            args.user, args.org_name, args.base_url, TOKEN, None
        )

    def test_verify_settings_called_with_master_org_name(self, api_class_mock):
        args = argparse.Namespace(
            subparser=cli.VERIFY_PARSER,
            user=USER,
            base_url=BASE_URL,
            org_name=ORG_NAME,
            token=TOKEN,
            master_org_name=MASTER_ORG_NAME,
        )

        cli.dispatch_command(args, None)

        api_class_mock.verify_settings.assert_called_once_with(
            args.user, args.org_name, args.base_url, TOKEN, MASTER_ORG_NAME
        )


@pytest.mark.parametrize("parser", cli.PARSER_NAMES)
def test_help_calls_add_arguments(monkeypatch, parser):
    """Test that the --help command causes _OrderedFormatter.add_arguments to
    be called. The reason this may not be the case is that
    HelpFormatter.add_arguments is not technically public, and so it could be
    removed or changed in future versions of Python.
    """
    called = False
    add_arguments = cli._OrderedFormatter.add_arguments

    def wrapper(self, *args, **kwargs):
        nonlocal called
        called = True
        add_arguments(self, *args, **kwargs)

    monkeypatch.setattr(
        "_repobee.cli._OrderedFormatter.add_arguments", wrapper
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.parse_args([parser, "--help"])

    assert exc_info.value.code == 0
    assert called


def test_create_parser_for_docs(no_plugins):
    """Test that the docs parser initializes correctly."""
    parser = cli.create_parser_for_docs()

    assert isinstance(parser, argparse.ArgumentParser)


class TestBaseParsing:
    """Test the basic functionality of parsing."""

    def test_show_all_opts_true_shows_configured_args(
        self, config_mock, capsys
    ):
        """Test that configured args are shown when show_all_opts is True."""
        with pytest.raises(SystemExit):
            cli.parse_args(
                [cli.SETUP_PARSER, "-h"], show_all_opts=True, ext_commands=[]
            )

        captured = capsys.readouterr()
        assert "--user" in captured.out
        assert "--base-url" in captured.out
        assert "--org-name" in captured.out
        assert "--master-org-name" in captured.out
        assert "--students-file" in captured.out
        assert "--token" in captured.out

    def test_show_all_opts_false_hides_configured_args(
        self, config_mock, capsys
    ):
        """Test that configured args are hidden when show_all_opts is False."""
        with pytest.raises(SystemExit):
            cli.parse_args(
                [cli.SETUP_PARSER, "-h"], show_all_opts=False, ext_commands=[]
            )

        captured = capsys.readouterr()
        assert "--user" not in captured.out
        assert "--base-url" not in captured.out
        assert "--org-name" not in captured.out
        assert "--master-org-name" not in captured.out
        assert "--students-file" not in captured.out
        assert "--token" not in captured.out

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
                    "--sf",
                    str(students_file),
                ]
            )

        assert "organization {} could not be found".format(ORG_NAME) in str(
            exc_info.value
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
                    "--sf",
                    str(students_file),
                ]
            )

        assert "bad credentials" in str(exc_info.value)

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
                    "--sf",
                    str(students_file),
                ]
            )

        assert "GitHub service could not be found, check the url" in str(
            exc_info.value
        )

    @pytest.mark.parametrize("parser", [cli.SETUP_PARSER, cli.UPDATE_PARSER])
    def test_master_org_overrides_target_org_for_master_repos(
        self, command_mock, api_instance_mock, students_file, parser
    ):
        parsed_args, _ = cli.parse_args(
            [
                cli.SETUP_PARSER,
                *COMPLETE_PUSH_ARGS,
                "--sf",
                str(students_file),
                "--mo",
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
            [parser, *COMPLETE_PUSH_ARGS, "--sf", str(students_file)]
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
            [parser, *COMPLETE_PUSH_ARGS, "--sf", str(students_file)]
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
                "--sf",
                str(students_file),
                "-t",
                token,
            ]
        )

        assert parsed_args.token == token

    @pytest.mark.parametrize(
        "url",
        [
            BASE_URL.replace("https://", non_tls_protocol)
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
            "-u",
            USER,
            "-o",
            ORG_NAME,
            "--bu",
            url,
            *BASE_PUSH_ARGS,
            "--sf",
            str(students_file),
        ]

        with pytest.raises(exception.ParseError) as exc_info:
            cli.parse_args(sys_args)

        assert "unsupported protocol in {}".format(url) in str(exc_info.value)


class TestExtensionCommands:
    """Parsing and dispatch tests for extension commands."""

    @pytest.fixture
    def mock_callback(self):
        """Return a mock callback function for use with an extension
        command.
        """
        yield MagicMock(
            spec=_repobee.ext.configwizard.create_extension_command
        )

    @pytest.fixture
    def ext_command(self, mock_callback):
        """Return a test extension command with an empty parser and a mocked
        callback.
        """
        return plug.ExtensionCommand(
            parser=plug.ExtensionParser(),
            name="test-command",
            help="help",
            description="description",
            callback=mock_callback,
        )

    @pytest.fixture
    def parsed_base_args_dict(self):
        return dict(
            base_url=BASE_URL,
            user=USER,
            org_name=ORG_NAME,
            token=TOKEN,
            traceback=False,
        )

    def test_parse_ext_command_that_does_not_require_api(
        self, ext_command, api_class_mock
    ):
        """If an extension command called does not require the API, then the
        command should not require the API base arguments, and no API should be
        created.
        """
        option = "--test-option"
        ext_command.parser.add_argument(
            option, action="store_true", required=True
        )

        parsed_args, api = cli.parse_args(
            [ext_command.name, option], ext_commands=[ext_command]
        )

        assert api is None
        assert parsed_args == argparse.Namespace(
            subparser=ext_command.name, test_option=True, traceback=False
        )

    def test_parse_ext_command_that_requires_api(
        self,
        ext_command,
        api_class_mock,
        api_instance_mock,
        parsed_base_args_dict,
    ):
        """If an extension command called requires the API, then the command
        should automatically get the requisite API arguments added to it
        """
        ext_command = plug.ExtensionCommand(
            *ext_command[: len(ext_command) - 1], requires_api=True
        )
        option = "--test-option"
        ext_command.parser.add_argument(
            option, action="store_true", required=True
        )

        parsed_args, api = cli.parse_args(
            [ext_command.name, *BASE_ARGS, option], ext_commands=[ext_command]
        )

        assert api is api_instance_mock
        api_class_mock.assert_called_once_with(BASE_URL, TOKEN, ORG_NAME, USER)
        assert parsed_args == argparse.Namespace(
            subparser=ext_command.name,
            test_option=True,
            **parsed_base_args_dict
        )

    def test_dispatch_ext_command_that_does_not_require_api(
        self, ext_command, mock_callback
    ):
        """The callback function should get None for the api argument, as it
        does not require the API.
        """
        option = "--test-option"
        ext_command.parser.add_argument(
            option, action="store_true", required=True
        )
        parsed_args = argparse.Namespace(
            subparser=ext_command.name, test_option=True, traceback=False
        )

        cli.dispatch_command(parsed_args, None, [ext_command])

        # for some reason, this completely sane assertion fails ALWAYS
        # mock_callback.assert_called_once_with(
        #   parsed_args, None)

        # this is a workaround
        assert len(mock_callback.call_args_list) == 1
        assert mock_callback.call_args_list[0] == mock.call(parsed_args, None)

    def test_dispatch_ext_command_that_requires_api(
        self,
        ext_command,
        mock_callback,
        api_instance_mock,
        parsed_base_args_dict,
    ):
        """The callback function should get ant api instance for the api
        argument, as it requires the API.
        """

        option = "--test-option"
        ext_command = plug.ExtensionCommand(
            *ext_command[: len(ext_command) - 1], requires_api=True
        )
        ext_command.parser.add_argument(
            option, action="store_true", required=True
        )
        parsed_args = argparse.Namespace(
            subparser=ext_command.name,
            test_option=True,
            **parsed_base_args_dict
        )

        cli.dispatch_command(parsed_args, api_instance_mock, [ext_command])

        # for some reason, this completely sane assertion fails ALWAYS
        # mock_callback.assert_called_once_with(
        #   parsed_args, api_instance_mock)

        # this is a workaround
        assert len(mock_callback.call_args_list) == 1
        assert mock_callback.call_args_list[0] == mock.call(
            parsed_args, api_instance_mock
        )


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
            (
                cli.CLOSE_ISSUE_PARSER,
                ["--mn", *REPO_NAMES, "-r", "some-regex"],
            ),
            (cli.OPEN_ISSUE_PARSER, ["--mn", *REPO_NAMES, "-i", ISSUE_PATH]),
        ],
    )
    STUDENT_PARSING_IDS = [
        "|".join([str(val) for val in line])
        for line in STUDENT_PARSING_PARAMS[1]
    ]

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_raises_if_students_file_is_not_a_file(self, parser, extra_args):
        not_a_file = "this-is-not-a-file"
        sys_args = [parser, *BASE_ARGS, "--sf", not_a_file, *extra_args]

        with pytest.raises(exception.FileError) as exc_info:
            cli.parse_args(sys_args)

        assert not_a_file in str(exc_info.value)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_listing_students(
        self, read_issue_mock, parser, extra_args
    ):
        """Test that the different subparsers parse arguments corectly when
        students are listed directly on the command line.
        """
        sys_args = [
            parser,
            *BASE_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
            *extra_args,
        ]

        parsed_args, _ = cli.parse_args(sys_args)

        assert parsed_args.students == list(STUDENTS)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_student_file(
        self, students_file, read_issue_mock, parser, extra_args
    ):
        """Test that the different subparsers read students correctly from
        file.
        """
        sys_args = [
            parser,
            *BASE_ARGS,
            "--sf",
            str(students_file),
            *extra_args,
        ]

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
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        with pytest.raises(exception.FileError) as exc_info:
            cli.parse_args(sys_args)

        assert "is empty" in str(exc_info.value)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parsers_raise_if_both_file_and_listing(
        self, read_issue_mock, students_file, parser, extra_args
    ):
        """Test that the student subparsers raise if students are both listed
        on the CLI, and a file is specified.
        """
        sys_args = [
            parser,
            *BASE_ARGS,
            "--sf",
            str(students_file),
            "-s",
            *STUDENTS_STRING.split(),
            *extra_args,
        ]

        with pytest.raises(SystemExit):
            cli.parse_args(sys_args)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_student_groups_parsed_correcly(
        self, empty_students_file, read_issue_mock, parser, extra_args
    ):
        """Test that putting multiple students on the same line in the students
        file results in them being in the same group.
        """
        # arrange
        groupings = (
            ["study"],
            ["buddy", "shuddy"],
            ["grape"],
            ["cat", "dog", "mouse"],
        )
        expected_groups = sorted(
            apimeta.Team(members=group) for group in groupings
        )
        empty_students_file.write(
            os.linesep.join([" ".join(group) for group in groupings])
        )
        sys_args = [
            parser,
            *BASE_ARGS,
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        # act
        parsed_args, _ = cli.parse_args(sys_args)

        # assert
        assert sorted(parsed_args.students) == expected_groups

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_raises_if_generated_team_name_too_long(
        self, empty_students_file, read_issue_mock, parser, extra_args
    ):
        """Test that the parser raises a ValueError if the team name generated
        from a group of students is longer than the maximum allowed by GitHub.
        """
        # arrange
        groupings = (
            ["buddy", "shuddy"],
            ["a" * apimeta.MAX_NAME_LENGTH, "b"],
            ["cat", "dog", "mouse"],
        )
        empty_students_file.write(
            os.linesep.join([" ".join(group) for group in groupings])
        )
        sys_args = [
            parser,
            *BASE_ARGS,
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        # act
        with pytest.raises(ValueError) as exc_info:
            cli.parse_args(sys_args)

        # assert
        assert "generated Team/Repository name is too long" in str(
            exc_info.value
        )


def assert_base_push_args(parsed_args, api):
    """Assert that the parsed arguments are consistend with the
    BASE_PUSH_ARGS.
    """
    assert parsed_args.org_name == ORG_NAME
    assert parsed_args.base_url == BASE_URL
    assert parsed_args.user == USER
    assert parsed_args.master_repo_names == list(REPO_NAMES)
    assert parsed_args.master_repo_urls == [
        generate_repo_url(rn, ORG_NAME) for rn in REPO_NAMES
    ]
    api.assert_called_once_with(BASE_URL, TOKEN, ORG_NAME, USER)


def assert_config_args(parser, parsed_args):
    """Asserts that the configured arguments are correct."""
    assert parsed_args.base_url == BASE_URL
    assert parsed_args.students == list(STUDENTS)
    assert parsed_args.org_name == ORG_NAME

    if parser in [cli.SETUP_PARSER, cli.UPDATE_PARSER]:
        assert parsed_args.user == USER


class TestConfig:
    """Tests that the configuration works properly."""

    @pytest.mark.parametrize(
        "parser, extra_args",
        [
            (cli.SETUP_PARSER, ["--mn", *REPO_NAMES]),
            (cli.UPDATE_PARSER, ["--mn", *REPO_NAMES]),
            (cli.OPEN_ISSUE_PARSER, ["--mn", *REPO_NAMES, "-i", ISSUE_PATH]),
        ],
    )
    def test_full_config(
        self, config_mock, read_issue_mock, parser, extra_args
    ):
        """Test that a fully configured file works. This means that
        base_url, org_name, user and student list are all
        preconfigured.
        """
        sys_args = [parser, *extra_args]

        parsed_args, _ = cli.parse_args(sys_args)
        assert_config_args(parser, parsed_args)

    # TODO test that not having base_url, org_name, user or
    # students_file in the config makes them required!

    def test_missing_option_is_required(self, config_missing_option):
        """Test that a config that is missing one option (that is not
        specified on the command line) causes a SystemExit on parsing.
        """
        # --mo is not required
        if config_missing_option == "--mo":
            return

        sys_args = [cli.SETUP_PARSER, "--mn", *REPO_NAMES]

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
        if config_missing_option == "--sf":  # must be file
            missing_arg = str(students_file)
        elif config_missing_option == "--bu":  # must be https url
            missing_arg = BASE_URL
        else:
            missing_arg = "whatever"

        sys_args = [
            cli.SETUP_PARSER,
            "--mn",
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
        sys_args = [
            parser,
            *COMPLETE_PUSH_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
        ]

        parsed_args, _ = cli.parse_args(sys_args)

        assert_base_push_args(parsed_args, api_class_mock)

    def test_finds_local_repo(self, mocker, api_instance_mock, parser):
        """Tests that the parsers pick up local repos when they are not
        found in the organization.
        """
        local_repo = REPO_NAMES[-1]
        mocker.patch(
            "_repobee.util.is_git_repo",
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

        sys_args = [
            parser,
            *COMPLETE_PUSH_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
        ]

        parsed_args, _ = cli.parse_args(sys_args)

        assert sorted(parsed_args.master_repo_urls) == sorted(expected)


class TestMigrateParser:
    """Tests for MIGRATE_PARSER."""

    NAMES = ["some-repo", "other-repo"]
    LOCAL_URIS = [
        pathlib.Path(os.path.abspath(name)).as_uri() for name in NAMES
    ]

    @pytest.fixture(autouse=True)
    def is_git_repo_mock(self, mocker):
        return mocker.patch(
            "_repobee.util.is_git_repo", autospec=True, return_value=True
        )

    def assert_migrate_args(self, parsed_args) -> bool:
        assert parsed_args.user == USER
        assert parsed_args.org_name == ORG_NAME
        assert parsed_args.base_url == BASE_URL
        assert parsed_args.master_repo_names == self.NAMES
        assert parsed_args.master_repo_urls == self.LOCAL_URIS

    def test_happy_path(self):
        sys_args = [cli.MIGRATE_PARSER, *BASE_ARGS, "--mn", *self.NAMES]

        parsed_args, _ = cli.parse_args(sys_args)

        self.assert_migrate_args(parsed_args)


class TestVerifyParser:
    """Tests for the VERIFY_PARSER."""

    def test_happy_path(self):
        sys_args = [cli.VERIFY_PARSER, *BASE_ARGS]

        args, _ = cli.parse_args(sys_args)

        assert args.subparser == cli.VERIFY_PARSER
        assert args.org_name == ORG_NAME
        assert args.base_url == BASE_URL
        assert args.user == USER


class TestCloneParser:
    """Tests for the CLONE_PARSER."""

    def test_happy_path(self, students_file, plugin_manager_mock):
        sys_args = [
            cli.CLONE_PARSER,
            *BASE_ARGS,
            "--mn",
            *REPO_NAMES,
            "--sf",
            str(students_file),
        ]

        args, _ = cli.parse_args(sys_args)

        assert args.subparser == cli.CLONE_PARSER
        assert args.org_name == ORG_NAME
        assert args.base_url == BASE_URL
        assert args.students == list(STUDENTS)
        # TODO assert with actual value
        plugin_manager_mock.hook.clone_parser_hook.assert_called_once_with(
            clone_parser=mock.ANY
        )
        plugin_manager_mock.hook.parse_args.assert_called_once_with(
            args=mock.ANY
        )

    @pytest.mark.parametrize(
        "parser, extra_args",
        [
            (
                cli.SETUP_PARSER,
                ["-s", *STUDENTS_STRING.split(), "--mn", *REPO_NAMES],
            ),
            (
                cli.UPDATE_PARSER,
                ["-s", *STUDENTS_STRING.split(), "--mn", *REPO_NAMES],
            ),
            (
                cli.OPEN_ISSUE_PARSER,
                [
                    "-s",
                    *STUDENTS_STRING.split(),
                    "--mn",
                    *REPO_NAMES,
                    "-i",
                    ISSUE_PATH,
                ],
            ),
            (
                cli.CLOSE_ISSUE_PARSER,
                [
                    "-s",
                    *STUDENTS_STRING.split(),
                    "--mn",
                    *REPO_NAMES,
                    "-r",
                    "some-regex",
                ],
            ),
            (cli.VERIFY_PARSER, []),
            (cli.MIGRATE_PARSER, ["--mn", *REPO_NAMES]),
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


class TestShowConfigParser:
    """Tests for repobee show-config"""

    def test_happy_path(self):
        args, _ = cli.parse_args([cli.SHOW_CONFIG_PARSER])

        assert args.subparser == cli.SHOW_CONFIG_PARSER


ASSIGN_REVIEWS_PARSER_OLD = "assign-peer-reviews"
PURGE_REVIEW_TEAMS_PARSER_OLD = "purge-peer-review-teams"
CHECK_REVIEW_PROGRESS_PARSER_OLD = "check-peer-review-progress"
DEPRECATED_PARSERS = {
    ASSIGN_REVIEWS_PARSER_OLD: tuples.Deprecation(
        replacement=cli.ASSIGN_REVIEWS_PARSER, remove_by="v2.0.0"
    ),
    PURGE_REVIEW_TEAMS_PARSER_OLD: tuples.Deprecation(
        replacement=cli.PURGE_REVIEW_TEAMS_PARSER, remove_by="v2.0.0"
    ),
    CHECK_REVIEW_PROGRESS_PARSER_OLD: tuples.Deprecation(
        replacement=cli.CHECK_REVIEW_PROGRESS_PARSER, remove_by="v2.0.0"
    ),
}


class TestCommandDeprecation:
    """Tests for deprecated commands, making sure they still work and have the
    same effect as the replacement commands.

    The semantics of deprecation of a command is that the old command should
    still work, but it should be parsed to the new command.
    """

    @pytest.fixture(autouse=True)
    def patch_deprecated_parsers(self, monkeypatch):
        monkeypatch.setattr(
            "_repobee.cli.DEPRECATED_PARSERS", DEPRECATED_PARSERS
        )

    @pytest.mark.parametrize(
        "deprecated_parser, current_parser, sys_args",
        [
            (
                ASSIGN_REVIEWS_PARSER_OLD,
                cli.ASSIGN_REVIEWS_PARSER,
                [
                    *BASE_ARGS,
                    "--mn",
                    "week-10",
                    "-i",
                    ISSUE_PATH,
                    "-s",
                    *STUDENTS_STRING.split(),
                    "-n",
                    "3",
                ],
            ),
            (
                PURGE_REVIEW_TEAMS_PARSER_OLD,
                cli.PURGE_REVIEW_TEAMS_PARSER,
                [
                    *BASE_ARGS,
                    "--mn",
                    "week-10",
                    "-s",
                    *STUDENTS_STRING.split(),
                ],
            ),
            (
                CHECK_REVIEW_PROGRESS_PARSER_OLD,
                cli.CHECK_REVIEW_PROGRESS_PARSER,
                [
                    *BASE_ARGS,
                    "--mn",
                    "week-10",
                    "-r",
                    "someregex",
                    "-n",
                    "3",
                    "-s",
                    *STUDENTS_STRING.split(),
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
