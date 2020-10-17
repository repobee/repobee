"""Integration tests for plugin functionality."""
import tempfile
import pathlib

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


def test_plugin_command_without_category(capsys):
    """A plugin command without category should be added as a 'category
    command'.

    Note that this test is run with repobee.main, as it previously broke there
    but not with repobee.run due to the implementation of tab completion.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
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
        f"recordname", plugins=[RecordName, _repobee.ext.ghclassroom]
    )

    assert actual_repo_name == expected_repo_name
