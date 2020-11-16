"""Integration tests for plugin functionality."""
import pytest

import _repobee
import _repobee.ext.ghclassroom
import repobee_plug as plug

from repobee_testhelpers import funcs
from repobee_testhelpers import const


def test_create_repo_with_plugin(platform_url):
    team = const.STUDENT_TEAMS[0]
    repo_name = "super-repo"
    description = "This is the description"
    private = True

    class CreateSingle(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            category=plug.cli.CoreCommand.repos, action="create-single"
        )
        team_name = plug.cli.option()
        repo_name = plug.cli.option()

        def command(self, api: plug.PlatformAPI):
            team = api.get_teams(team_names=[self.team_name])
            api.create_repo(
                self.repo_name,
                description=description,
                private=private,
                team=team,
            )

    funcs.run_repobee(
        f"repos create-single --bu {platform_url} "
        f"--team-name {team.name} --repo-name {repo_name}",
        plugins=[CreateSingle],
    )

    existing_repos = funcs.get_repos(platform_url)

    matching_repo = next(
        (repo for repo in existing_repos if repo.name == repo_name), None
    )

    assert matching_repo.name == repo_name
    assert matching_repo.description == description
    assert matching_repo.private == private


def test_plugin_command_without_category(capsys, workdir):
    """A plugin command without category should be added as a 'category
    command'.

    Note that this test is run with repobee.main, as it previously broke there
    but not with repobee.run due to the implementation of tab completion.
    """
    hello_py = workdir / "hello.py"
    hello_py.write_text(
        """
import repobee_plug as plug
class HelloWorld(plug.Plugin, plug.cli.Command):
    def command(self):
        plug.echo("Hello, world!")
""",
        encoding="utf8",
    )

    _repobee.main.main(["repobee", "-p", str(hello_py), "helloworld"])

    assert "Hello, world!" in capsys.readouterr().out


def test_ghclassroom_plugin_changes_repo_name_generation():
    """Test that the ghclassroom plugin correctly changes the repo name
    generation even for other plugins."""
    assignment = "task"
    student = "eve"
    expected_repo_name = f"{assignment}-{student}"
    actual_repo_name = None

    class RecordName(plug.Plugin, plug.cli.Command):
        def command(self):
            nonlocal actual_repo_name
            actual_repo_name = plug.generate_repo_name(
                team_name=student, assignment_name=assignment
            )

    funcs.run_repobee(
        "recordname", plugins=[RecordName, _repobee.ext.ghclassroom]
    )

    assert actual_repo_name == expected_repo_name


def test_discover_repos_parser_does_not_discover_repos_if_flag_not_specified(
    platform_url, with_student_repos
):
    """Test that the discovery mechanism is inactive if --discover-repos flag
    is not specified.
    """
    args = []
    student = "slarse"
    assignment = "epic-task"

    class Check(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            base_parsers=[
                plug.cli.BaseParser.STUDENTS,
                plug.cli.BaseParser.REPO_DISCOVERY,
            ]
        )

        def command(self, api):
            nonlocal args
            args = self.args

    funcs.run_repobee(
        f"check --base-url {platform_url} "
        f"-s {student} "
        f"-a {assignment}",
        plugins=[Check],
    )

    assert "repos" not in args


def test_discover_repos_parser_discovers_repos_if_flag_is_specified(
    platform_url, with_student_repos
):
    """Test that the discovery mechanism kicks in if --discover-repos is
    specified.
    """
    discovered_repos = []

    class Check(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            base_parsers=[
                plug.cli.BaseParser.STUDENTS,
                plug.cli.BaseParser.REPO_DISCOVERY,
            ]
        )

        def command(self, api):
            nonlocal discovered_repos
            discovered_repos = list(self.args.repos)

    funcs.run_repobee(
        f"check --base-url {platform_url} "
        f"--sf {const.STUDENTS_FILE} "
        f"--discover-repos",
        plugins=[Check],
    )

    expected_num_repos = len(const.TEMPLATE_REPO_NAMES) * len(
        const.STUDENT_TEAMS
    )
    assert len(discovered_repos) == expected_num_repos


def test_repo_discovery_parser_requires_api():
    """It should not be possible to have a plugin command that requires the
    repo discovery parser, but not the platform API, as the former needs the
    latter to search for repos."""

    with pytest.raises(plug.PlugError) as exc_info:

        class InvalidCommand(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(
                base_parsers=[
                    plug.cli.BaseParser.STUDENTS,
                    plug.cli.BaseParser.REPO_DISCOVERY,
                ]
            )

            def command(self):
                pass

    assert (
        "REPO_DISCOVERY parser requires command function to use api argument"
        in str(exc_info.value)
    )


def test_repo_discovery_parser_requires_student_parser():
    """The repo discovery parser does not make any sense without the student
    parser, as the whole idea is to search student teams for repositories.
    """

    with pytest.raises(plug.PlugError) as exc_info:

        class InvalidCommand(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(
                base_parsers=[plug.cli.BaseParser.REPO_DISCOVERY]
            )

            def command(self, api):
                pass

    assert "REPO_DISCOVERY parser requires STUDENT parser" in str(
        exc_info.value
    )


def test_plugin_crash_error_message(capsys, workdir):
    """"""
    crash_py = workdir / "crash.py"
    crash_py.write_text(
        """
import repobee_plug as plug
class Crash(plug.Plugin, plug.cli.Command):
    def command(self):
        raise plug.PlugError("this is an error")
""",
        encoding="utf8",
    )

    with pytest.raises(SystemExit):
        _repobee.main.main(["repobee", "-p", str(crash_py), "crash"])

    assert "A plugin exited with an error" in str(capsys.readouterr().err)
