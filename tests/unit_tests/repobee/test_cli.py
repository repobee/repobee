import os
import pathlib
import argparse
import collections
import itertools
from unittest import mock

import pytest

import repobee_plug as plug

import _repobee
import _repobee.cli.dispatch
import _repobee.cli.parsing
import _repobee.ext
import _repobee.ext.query
import _repobee.constants
import _repobee.plugin
import _repobee.ext.defaults.configwizard
import repobee_plug.cli
from _repobee.cli import mainparser
from _repobee import exception

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
TEMPLATE_ORG_NAME = constants.TEMPLATE_ORG_NAME
TOKEN = constants.TOKEN

EMPTY_PATH = pathlib.Path(".")

ASSIGNMENT_NAMES = ("week-1", "week-2", "week-3")
REPO_URLS = tuple(
    map(lambda rn: generate_repo_url(rn, ORG_NAME), ASSIGNMENT_NAMES)
)

BASE_ARGS = ["-u", USER, "--bu", BASE_URL, "-o", ORG_NAME, "-t", TOKEN]
BASE_PUSH_ARGS = ["-a", *ASSIGNMENT_NAMES]
COMPLETE_PUSH_ARGS = [*BASE_ARGS, *BASE_PUSH_ARGS]

# parsed args without subparser
VALID_PARSED_ARGS = dict(
    org_name=ORG_NAME,
    template_org_name=TEMPLATE_ORG_NAME,
    base_url=BASE_URL,
    user=USER,
    template_repo_urls=REPO_URLS,
    assignments=ASSIGNMENT_NAMES,
    students=list(STUDENTS),
    issue=ISSUE,
    title_regex="some regex",
    traceback=False,
    state=plug.IssueState.OPEN,
    show_body=True,
    author=None,
    token=TOKEN,
    num_reviews=1,
    hook_results_file=None,
    repos=[
        plug.StudentRepo(
            name=plug.generate_repo_name(team, master_name),
            team=team,
            url=generate_repo_url(
                plug.generate_repo_name(team, master_name), ORG_NAME
            ),
        )
        for team, master_name in itertools.product(STUDENTS, ASSIGNMENT_NAMES)
    ],
)


@pytest.fixture(autouse=True)
def load_default_plugins_auto(load_default_plugins):
    """The only point of this fixture is to make load_default_plugins
    autouse=True.
    """
    yield


@pytest.fixture
def no_plugins(load_default_plugins):
    """Unregister any registered plugins."""
    for plugin in plug.manager.get_plugins():
        plug.manager.unregister(plugin=plugin)


@pytest.fixture
def command_mock(mocker):
    return mocker.patch("_repobee.cli.dispatch.command", autospec=True)


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


@pytest.fixture(scope="function", params=iter(repobee_plug.cli.CoreCommand))
def parsed_args_all_subparsers(request):
    """Parametrized fixture which returns a namespace for each of the
    subparsers. These arguments are valid for all subparsers, even though
    many will only use some of the arguments.
    """
    return argparse.Namespace(**request.param.asdict(), **VALID_PARSED_ARGS)


@pytest.fixture(
    scope="function",
    params=[
        exception.PushFailedError("some message", 128, b"error", "someurl"),
        exception.CloneFailedError("some message", 128, b"error", "someurl"),
        exception.GitError("some message", 128, b"error"),
        plug.PlatformError("some message"),
    ],
)
def command_all_raise_mock(command_mock, dummyapi_instance, request):
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
    dummyapi_instance.verify_settings = raise_
    return command_mock


@pytest.fixture
def hook_result_mapping():
    """A hook result mapping for use as a mocked return value to commands that
    return hook results (e.g. command.clone_repos).
    """
    hook_results = collections.defaultdict(list)
    for repo_name, hook_name, status, msg, data in [
        (
            "slarse-task-1",
            "junit4",
            plug.Status.SUCCESS,
            "All tests passed",
            {"extra": "data", "arbitrary": {"nesting": "here"}},
        ),
        (
            "slarse-task-1",
            "javac",
            plug.Status.ERROR,
            "Some stuff failed",
            None,
        ),
        (
            "glassey-task-2",
            "pylint",
            plug.Status.WARNING,
            "-10/10 code quality",
            None,
        ),
    ]:
        hook_results[repo_name].append(
            plug.Result(name=hook_name, status=status, msg=msg, data=data)
        )
    return dict(hook_results)


class TestDispatchCommand:
    """Test the handling of parsed arguments."""

    @pytest.mark.parametrize(
        "action, command_func",
        [
            (
                repobee_plug.cli.CoreCommand.repos.clone,
                "_repobee.command.clone_repos",
            ),
            (
                repobee_plug.cli.CoreCommand.issues.list,
                "_repobee.command.list_issues",
            ),
        ],
    )
    def test_writes_hook_results_correctly(
        self,
        tmpdir,
        hook_result_mapping,
        dummyapi_instance,
        action,
        command_func,
    ):
        expected_filepath = pathlib.Path(".").resolve() / "results.json"
        expected_json = plug.result_mapping_to_json(hook_result_mapping)
        args_dict = dict(VALID_PARSED_ARGS)
        args_dict["hook_results_file"] = str(expected_filepath)
        with mock.patch(
            "_repobee.util.atomic_write", autospec=True
        ) as write, mock.patch(
            command_func, autospec=True, return_value=hook_result_mapping
        ):
            args = argparse.Namespace(**action.asdict(), **args_dict)
            _repobee.cli.dispatch.dispatch_command(
                args, dummyapi_instance, EMPTY_PATH
            )

        write.assert_called_once_with(expected_json, expected_filepath)

    def test_does_not_write_hook_results_if_there_are_none(
        self, tmpdir, dummyapi_instance
    ):
        """Test that no file is created if there are no hook results, even if
        --hook-results-file is specified.
        """
        expected_filepath = pathlib.Path(".").resolve() / "results.json"
        args_dict = dict(VALID_PARSED_ARGS)
        args_dict["hook_results_file"] = str(expected_filepath)
        action = repobee_plug.cli.CoreCommand.repos.clone

        with mock.patch(
            "_repobee.util.atomic_write", autospec=True
        ) as write, mock.patch(
            "_repobee.command.clone_repos", autospec=True, return_value={}
        ):
            args = argparse.Namespace(**action.asdict(), **args_dict)
            _repobee.cli.dispatch.dispatch_command(
                args, dummyapi_instance, EMPTY_PATH
            )

        assert not write.called

    def test_no_crash_on_valid_args(
        self, parsed_args_all_subparsers, dummyapi_instance, command_mock
    ):
        """Test that valid arguments does not result in crash. Only validates
        that there are no crashes, does not validate any other behavior!"""
        _repobee.cli.dispatch.dispatch_command(
            parsed_args_all_subparsers, dummyapi_instance, EMPTY_PATH
        )

    def test_setup_student_repos_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.repos.setup.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.setup_student_repos.assert_called_once_with(
            args.template_repo_urls, args.students, dummyapi_instance
        )

    def test_update_student_repos_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.repos.update.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.update_student_repos.assert_called_once_with(
            args.template_repo_urls,
            args.students,
            dummyapi_instance,
            issue=args.issue,
        )

    def test_create_teams_called_with_correct_args(
        self, dummyapi_instance, command_mock
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.teams.create.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.create_teams.assert_called_once_with(
            list(args.students), plug.TeamPermission.PUSH, dummyapi_instance
        )

    def test_open_issue_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.issues.open.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.open_issue.assert_called_once_with(
            args.issue, args.assignments, args.students, dummyapi_instance
        )

    def test_close_issue_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.issues.close.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.close_issue.assert_called_once_with(
            args.title_regex, args.repos, dummyapi_instance
        )

    def test_migrate_repos_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.repos.migrate.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.migrate_repos.assert_called_once_with(
            args.template_repo_urls, dummyapi_instance
        )

    def test_clone_repos_called_with_correct_args(
        self, command_mock, dummyapi_instance
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.repos.clone.asdict(),
            **VALID_PARSED_ARGS,
        )

        _repobee.cli.dispatch.dispatch_command(
            args, dummyapi_instance, EMPTY_PATH
        )

        command_mock.clone_repos.assert_called_once_with(
            args.repos, dummyapi_instance
        )

    def test_verify_settings_called_with_correct_args(
        self, monkeypatch, dummyapi_class
    ):
        # regular mockaing is broken for static methods, it seems, produces
        # non-callable so using monkeypatch instead
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.config.verify.asdict(),
            user=USER,
            base_url=BASE_URL,
            token=TOKEN,
            org_name=ORG_NAME,
            template_org_name=None,
        )
        mock_verify_settings = mock.MagicMock(
            spec=dummyapi_class.verify_settings
        )
        monkeypatch.setattr(
            dummyapi_class, "verify_settings", mock_verify_settings
        )

        _repobee.cli.dispatch.dispatch_command(args, None, EMPTY_PATH)

        mock_verify_settings.assert_called_once_with(
            args.user, args.org_name, args.base_url, TOKEN, None
        )

    def test_verify_settings_called_with_template_org_name(
        self, dummyapi_class, monkeypatch
    ):
        args = argparse.Namespace(
            **repobee_plug.cli.CoreCommand.config.verify.asdict(),
            user=USER,
            base_url=BASE_URL,
            org_name=ORG_NAME,
            token=TOKEN,
            template_org_name=TEMPLATE_ORG_NAME,
        )
        mock_verify_settings = mock.MagicMock(
            spec=dummyapi_class.verify_settings
        )
        monkeypatch.setattr(
            dummyapi_class, "verify_settings", mock_verify_settings
        )

        _repobee.cli.dispatch.dispatch_command(args, None, EMPTY_PATH)

        mock_verify_settings.assert_called_once_with(
            args.user, args.org_name, args.base_url, TOKEN, TEMPLATE_ORG_NAME
        )


@pytest.mark.parametrize("action", repobee_plug.cli.CoreCommand.iter_actions())
def test_help_calls_add_arguments(monkeypatch, action):
    """Test that the --help command causes _OrderedFormatter.add_arguments to
    be called. The reason this may not be the case is that
    HelpFormatter.add_arguments is not technically public, and so it could be
    removed or changed in future versions of Python.
    """
    called = False
    add_arguments = mainparser._OrderedFormatter.add_arguments

    def wrapper(self, *args, **kwargs):
        nonlocal called
        called = True
        add_arguments(self, *args, **kwargs)

    monkeypatch.setattr(
        "_repobee.cli.mainparser._OrderedFormatter.add_arguments", wrapper
    )

    with pytest.raises(SystemExit) as exc_info:
        _repobee.cli.parsing.handle_args([*action.as_name_tuple(), "--help"])

    assert exc_info.value.code == 0
    assert called


def test_create_parser_for_docs(no_plugins):
    """Test that the docs parser initializes correctly."""
    parser = mainparser.create_parser_for_docs()

    assert isinstance(parser, argparse.ArgumentParser)


class TestBaseParsing:
    """Test the basic functionality of parsing."""

    def test_show_all_opts_true_shows_configured_args(
        self, config_mock, capsys
    ):
        """Test that configured args are shown when show_all_opts is True."""
        with pytest.raises(SystemExit):
            _repobee.cli.parsing.handle_args(
                [
                    *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                    "-h",
                ],
                show_all_opts=True,
            )

        captured = capsys.readouterr()
        assert "--user" in captured.out
        assert "--base-url" in captured.out
        assert "--org-name" in captured.out
        assert "--template-org-name" in captured.out
        assert "--students-file" in captured.out
        assert "--token" in captured.out

    def test_show_all_opts_false_hides_configured_args(
        self, config_mock, capsys
    ):
        """Test that configured args are hidden when show_all_opts is False."""
        with pytest.raises(SystemExit):
            _repobee.cli.parsing.handle_args(
                [
                    *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
                    "-h",
                ],
                show_all_opts=False,
            )

        captured = capsys.readouterr()
        assert "--user" not in captured.out
        assert "--base-url" not in captured.out
        assert "--org-name" not in captured.out
        assert "--template-org-name" not in captured.out
        assert "--students-file" not in captured.out
        assert "--token" not in captured.out

    @pytest.mark.parametrize(
        "action",
        [
            repobee_plug.cli.CoreCommand.repos.setup,
            repobee_plug.cli.CoreCommand.repos.update,
        ],
    )
    def test_template_org_overrides_target_org_for_master_repos(
        self, command_mock, dummyapi_instance, students_file, action
    ):
        print(plug.manager.get_plugins())
        parsed_args, _ = _repobee.cli.parsing.handle_args(
            [
                *action.as_name_tuple(),
                *COMPLETE_PUSH_ARGS,
                "--sf",
                str(students_file),
                "--to",
                TEMPLATE_ORG_NAME,
            ]
        )

        assert all(
            [
                "/" + TEMPLATE_ORG_NAME + "/" in url
                for url in parsed_args.template_repo_urls
            ]
        )

    @pytest.mark.parametrize(
        "action",
        [
            repobee_plug.cli.CoreCommand.repos.setup,
            repobee_plug.cli.CoreCommand.repos.update,
        ],
    )
    def test_template_org_name_defaults_to_org_name(
        self, dummyapi_instance, students_file, action
    ):
        parsed_args, _ = _repobee.cli.parsing.handle_args(
            [
                *action.as_name_tuple(),
                *COMPLETE_PUSH_ARGS,
                "--sf",
                str(students_file),
            ]
        )

        assert all(
            [
                "/" + ORG_NAME + "/" in url
                for url in parsed_args.template_repo_urls
            ]
        )

    @pytest.mark.parametrize(
        "action",
        [
            repobee_plug.cli.CoreCommand.repos.setup,
            repobee_plug.cli.CoreCommand.repos.update,
        ],
    )
    def test_token_env_variable_picked_up(
        self, dummyapi_instance, students_file, action
    ):
        parsed_args, _ = _repobee.cli.parsing.handle_args(
            [
                *action.as_name_tuple(),
                *COMPLETE_PUSH_ARGS,
                "--sf",
                str(students_file),
            ]
        )

        assert parsed_args.token == TOKEN

    @pytest.mark.parametrize(
        "action",
        [
            repobee_plug.cli.CoreCommand.repos.setup,
            repobee_plug.cli.CoreCommand.repos.update,
        ],
    )
    def test_token_cli_arg_picked_up(
        self, mocker, dummyapi_instance, students_file, action
    ):
        mocker.patch("os.getenv", return_value="")
        token = "supersecretothertoken"
        parsed_args, _ = _repobee.cli.parsing.handle_args(
            [
                *action.as_name_tuple(),
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
        self, dummyapi_instance, students_file, url
    ):
        """Test that a non https url causes parse-args to raise. Sending the token
        over an unencrypted connection would be a security risk, so https is
        required.
        """
        sys_args = [
            *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
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
            _repobee.cli.parsing.handle_args(sys_args)

        assert "unsupported protocol in {}".format(url) in str(exc_info.value)

    def test_correctly_parsers_teams_create(
        self, dummyapi_instance, students_file
    ):
        """Test that the ``teams create`` command is correctly parsed."""
        sys_args = [
            *repobee_plug.cli.CoreCommand.teams.create.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(students_file),
        ]

        parsed_args, api = _repobee.cli.parsing.handle_args(sys_args)

        assert api == dummyapi_instance
        assert parsed_args.students == list(STUDENTS)
        assert parsed_args.assignments is None
        assert parsed_args.template_repo_urls is None


class TestStudentParsing:
    """Tests for the parsers that use the `--students` and `--students-file`
    arguments.
    """

    STUDENT_PARSING_PARAMS = (
        "action, extra_args",
        [
            (repobee_plug.cli.CoreCommand.repos.setup, BASE_PUSH_ARGS),
            (repobee_plug.cli.CoreCommand.repos.update, BASE_PUSH_ARGS),
            (
                repobee_plug.cli.CoreCommand.issues.close,
                ["-a", *ASSIGNMENT_NAMES, "-r", "some-regex"],
            ),
            (
                repobee_plug.cli.CoreCommand.issues.open,
                ["-a", *ASSIGNMENT_NAMES, "-i", ISSUE_PATH],
            ),
        ],
    )
    STUDENT_PARSING_IDS = [
        "|".join([str(val) for val in line])
        for line in STUDENT_PARSING_PARAMS[1]
    ]

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_raises_if_students_file_is_not_a_file(self, action, extra_args):
        not_a_file = "this-is-not-a-file"
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            not_a_file,
            *extra_args,
        ]

        with pytest.raises(exception.FileError) as exc_info:
            _repobee.cli.parsing.handle_args(sys_args)

        assert not_a_file in str(exc_info.value)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_listing_students(
        self, read_issue_mock, action, extra_args
    ):
        """Test that the different subparsers parse arguments corectly when
        students are listed directly on the command line.
        """
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
            *extra_args,
        ]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert parsed_args.students == list(STUDENTS)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parser_student_file(
        self, students_file, read_issue_mock, action, extra_args
    ):
        """Test that the different subparsers read students correctly from
        file.
        """
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(students_file),
            *extra_args,
        ]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert parsed_args.students == list(STUDENTS)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_student_parsers_raise_on_empty_student_file(
        self, read_issue_mock, empty_students_file, action, extra_args
    ):
        """Test that an error is raised if the student file is empty."""
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        with pytest.raises(exception.FileError) as exc_info:
            _repobee.cli.parsing.handle_args(sys_args)

        assert "is empty" in str(exc_info.value)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_parsers_raise_if_both_file_and_listing(
        self, read_issue_mock, students_file, action, extra_args
    ):
        """Test that the student subparsers raise if students are both listed
        on the CLI, and a file is specified.
        """
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(students_file),
            "-s",
            *STUDENTS_STRING.split(),
            *extra_args,
        ]

        with pytest.raises(SystemExit):
            _repobee.cli.parsing.handle_args(sys_args)

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_student_groups_parsed_correcly(
        self, empty_students_file, read_issue_mock, action, extra_args
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
            plug.StudentTeam(members=group) for group in groupings
        )
        empty_students_file.write(
            os.linesep.join([" ".join(group) for group in groupings])
        )
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        # act
        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        # assert
        assert sorted(parsed_args.students) == expected_groups

    @pytest.mark.parametrize(*STUDENT_PARSING_PARAMS, ids=STUDENT_PARSING_IDS)
    def test_raises_if_generated_team_name_too_long(
        self, empty_students_file, read_issue_mock, action, extra_args
    ):
        """Test that the parser raises a ValueError if the team name generated
        from a group of students is longer than the maximum allowed by GitHub.
        """
        # arrange
        groupings = (
            ["buddy", "shuddy"],
            # TODO remove dependency on _apimeta, it's private!
            ["a" * plug.localreps.MAX_NAME_LENGTH, "b"],
            ["cat", "dog", "mouse"],
        )
        empty_students_file.write(
            os.linesep.join([" ".join(group) for group in groupings])
        )
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "--sf",
            str(empty_students_file),
            *extra_args,
        ]

        # act
        with pytest.raises(ValueError) as exc_info:
            _repobee.cli.parsing.handle_args(sys_args)

        # assert
        assert "generated Team/Repository name is too long" in str(
            exc_info.value
        )


def assert_base_push_args(parsed_args):
    """Assert that the parsed arguments are consistend with the
    BASE_PUSH_ARGS.
    """
    assert parsed_args.org_name == ORG_NAME
    assert parsed_args.base_url == BASE_URL
    assert parsed_args.user == USER
    assert parsed_args.assignments == list(ASSIGNMENT_NAMES)
    assert parsed_args.template_repo_urls == [
        generate_repo_url(rn, ORG_NAME) for rn in ASSIGNMENT_NAMES
    ]
    assert parsed_args.base_url == BASE_URL
    assert parsed_args.token == TOKEN
    assert parsed_args.org_name == ORG_NAME
    assert parsed_args.user == USER


def assert_config_args(action, parsed_args):
    """Asserts that the configured arguments are correct."""
    assert parsed_args.base_url == BASE_URL
    assert parsed_args.students == list(STUDENTS)
    assert parsed_args.org_name == ORG_NAME

    if action in [
        repobee_plug.cli.CoreCommand.repos.setup,
        repobee_plug.cli.CoreCommand.repos.update,
    ]:
        assert parsed_args.user == USER


class TestConfig:
    """Tests that the configuration works properly."""

    @pytest.mark.parametrize(
        "action, extra_args",
        [
            (
                repobee_plug.cli.CoreCommand.repos.setup,
                ["-a", *ASSIGNMENT_NAMES],
            ),
            (
                repobee_plug.cli.CoreCommand.repos.update,
                ["-a", *ASSIGNMENT_NAMES],
            ),
            (
                repobee_plug.cli.CoreCommand.issues.open,
                ["-a", *ASSIGNMENT_NAMES, "-i", ISSUE_PATH],
            ),
        ],
    )
    def test_full_config(
        self, config_mock, read_issue_mock, action, extra_args
    ):
        """Test that a fully configured file works. This means that
        base_url, org_name, user and student list are all
        preconfigured.
        """
        sys_args = [*action.as_name_tuple(), *extra_args]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)
        assert_config_args(action, parsed_args)

    # TODO test that not having base_url, org_name, user or
    # students_file in the config makes them required!

    def test_missing_option_is_required(self, config_missing_option):
        """Test that a config that is missing one option (that is not
        specified on the command line) causes a SystemExit on parsing.
        """
        # --to is not required
        if config_missing_option == "--to":
            return

        sys_args = [
            *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
            "-a",
            *ASSIGNMENT_NAMES,
        ]

        with pytest.raises(SystemExit):
            parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)
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
            *repobee_plug.cli.CoreCommand.repos.setup.as_name_tuple(),
            "-a",
            *ASSIGNMENT_NAMES,
            config_missing_option,
            missing_arg,
        ]

        # only asserts that there is no crash
        _repobee.cli.parsing.handle_args(sys_args)


@pytest.mark.parametrize(
    "action",
    [
        repobee_plug.cli.CoreCommand.repos.setup,
        repobee_plug.cli.CoreCommand.repos.update,
    ],
)
class TestSetupAndUpdateParsers:
    """Tests that are in common for setup and update."""

    def test_happy_path(self, action):
        """Tests standard operation of the parsers."""
        sys_args = [
            *action.as_name_tuple(),
            *COMPLETE_PUSH_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
        ]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert_base_push_args(parsed_args)

    def test_finds_local_repo(self, mocker, dummyapi_instance, action):
        """Tests that the parsers pick up local repos when they are not
        found in the organization.
        """
        local_repo = ASSIGNMENT_NAMES[-1]
        mocker.patch(
            "_repobee.util.is_git_repo",
            side_effect=lambda path: path.endswith(local_repo),
        )
        expected_urls = [
            generate_repo_url(name, ORG_NAME)
            for name in ASSIGNMENT_NAMES
            if name != local_repo
        ]
        expected_uris = [pathlib.Path(os.path.abspath(local_repo)).as_uri()]
        expected = expected_urls + expected_uris

        sys_args = [
            *action.as_name_tuple(),
            *COMPLETE_PUSH_ARGS,
            "-s",
            *STUDENTS_STRING.split(),
            "--allow-local-templates",
        ]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert sorted(parsed_args.template_repo_urls) == sorted(expected)


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
        assert parsed_args.assignments == self.NAMES
        assert parsed_args.template_repo_urls == self.LOCAL_URIS

    def test_happy_path(self):
        sys_args = [
            *repobee_plug.cli.CoreCommand.repos.migrate.as_name_tuple(),
            *BASE_ARGS,
            "-a",
            *self.NAMES,
            "--allow-local-templates",
        ]

        parsed_args, _ = _repobee.cli.parsing.handle_args(sys_args)

        self.assert_migrate_args(parsed_args)


class TestVerifyParser:
    """Tests for the VERIFY_PARSER."""

    def test_happy_path(self):
        action = repobee_plug.cli.CoreCommand.config.verify
        sys_args = [*action.as_name_tuple(), *BASE_ARGS]

        args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert (args.category, args.action) == action.astuple()
        assert args.org_name == ORG_NAME
        assert args.base_url == BASE_URL
        assert args.user == USER


class TestCloneParser:
    """Tests for the CLONE_PARSER."""

    def test_happy_path(self, students_file):
        action = repobee_plug.cli.CoreCommand.repos.clone
        sys_args = [
            *action.as_name_tuple(),
            *BASE_ARGS,
            "-a",
            *ASSIGNMENT_NAMES,
            "--sf",
            str(students_file),
        ]

        args, _ = _repobee.cli.parsing.handle_args(sys_args)

        assert (args.category, args.action) == action.astuple()
        assert args.org_name == ORG_NAME
        assert args.base_url == BASE_URL
        assert args.students == list(STUDENTS)


class TestShowConfigParser:
    """Tests for repobee show-config"""

    def test_happy_path(self):
        args, _ = _repobee.cli.parsing.handle_args(
            repobee_plug.cli.CoreCommand.config.show.as_name_tuple()
        )

        assert (
            args.category,
            args.action,
        ) == repobee_plug.cli.CoreCommand.config.show.astuple()
