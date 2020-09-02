"""Tests for the repos category of commands."""
import pathlib
import tempfile

from typing import List, Mapping, Tuple, Iterable

import git
import pytest

import _repobee.ext.javac

import repobee_plug as plug
from repobee_testhelpers import localapi
from repobee_testhelpers import funcs
from _repobee import exception


from repobee_testhelpers.const import (
    STUDENT_TEAMS,
    TEMPLATE_REPO_NAMES,
    TEMPLATE_REPOS_ARG,
)


def assert_student_repos_match_templates(
    student_teams: List[plug.StudentTeam],
    template_repo_names: List[str],
    repos: List[localapi.Repo],
):
    """Assert that the content of the student repos matches the content of the
    respective template repos.
    """
    repos_dict = {repo.name: repo.path for repo in repos}
    _assert_repos_match_templates(
        student_teams,
        template_repo_names,
        funcs.template_repo_hashes(),
        repos_dict,
    )


def assert_cloned_student_repos_match_templates(
    student_teams: List[plug.StudentTeam],
    template_repo_names: List[str],
    workdir: pathlib.Path,
):
    repos_dict = {
        plug.generate_repo_name(team.name, template_repo_name): workdir
        / team.name
        / plug.generate_repo_name(team.name, template_repo_name)
        for team in student_teams
        for template_repo_name in template_repo_names
    }
    _assert_repos_match_templates(
        student_teams,
        template_repo_names,
        funcs.template_repo_hashes(),
        repos_dict,
    )


def _assert_repos_match_templates(
    student_teams: List[plug.StudentTeam],
    template_repo_names: List[str],
    template_repo_hashes: Mapping[str, str],
    repos_dict: Mapping[str, pathlib.Path],
):
    num_asserts = 0
    for template_name in template_repo_names:
        student_repos = [
            repos_dict[repo_name]
            for repo_name in plug.generate_repo_names(
                student_teams, [template_name]
            )
        ]
        assert len(student_repos) == len(student_teams)

        for repo in student_repos:
            num_asserts += 1
            assert funcs.tree_hash(repo) == template_repo_hashes[template_name]

    assert num_asserts == len(student_teams) * len(
        template_repo_names
    ), "Performed fewer asserts than expected"


class TestSetup:
    """Tests for the ``repos setup`` command."""

    def test_setup_single_template_repo(self, platform_dir, platform_url):
        template_repo_name = TEMPLATE_REPO_NAMES[0]
        funcs.run_repobee(
            f"repos setup -a {template_repo_name} "
            f"--base-url {platform_url}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, [template_repo_name], funcs.get_repos(platform_url)
        )

    def test_setup_multiple_template_repos(self, platform_dir, platform_url):
        funcs.run_repobee(
            f"repos setup -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, funcs.get_repos(platform_url)
        )

    def test_setup_multiple_template_repos_twice(
        self, platform_dir, platform_url
    ):
        """Running setup command twice should have the same effect as running
        it once.
        """
        for _ in range(2):
            funcs.run_repobee(
                f"repos setup -a {TEMPLATE_REPOS_ARG} "
                f"--base-url {platform_url} "
            )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, funcs.get_repos(platform_url)
        )

    def test_setup_with_local_repos(self, platform_url):
        """Test running the setup command with the names of local
        repositories. That is to say, repos that are not in the
        template organization.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # arrange
            template_repo_dir = pathlib.Path(tmpdir)
            template_repo_hashes = {}

            task_34 = template_repo_dir / "task-34"
            task_55 = template_repo_dir / "task-55"
            template_repo_hashes[task_34.name] = create_local_repo(
                task_34, [("somefile.txt", "This is task 34!")]
            )
            template_repo_hashes[task_55.name] = create_local_repo(
                task_55, [("hello.py", "print('hello, world!')")]
            )

            # act
            funcs.run_repobee(
                f"repos setup -a {task_55.name} {task_34.name} "
                f"--base-url {platform_url} "
                "--allow-local-templates",
                workdir=template_repo_dir,
            )

            # assert
            repo_dict = {
                repo.name: repo.path for repo in funcs.get_repos(platform_url)
            }

            _assert_repos_match_templates(
                STUDENT_TEAMS,
                [task_34.name, task_55.name],
                template_repo_hashes,
                repo_dict,
            )

    def test_does_not_push_to_existing_repos(
        self, platform_url, with_student_repos, capsys
    ):
        """This command should not push to existing repos, that's for the
        ``update`` command to do.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # arrange
            template_repo_dir = pathlib.Path(tmpdir)
            task = template_repo_dir / TEMPLATE_REPO_NAMES[0]
            create_local_repo(task, [("best/file/ever.txt", "content")])

            # act
            # this push would fail if it was attempted, as the repo
            # content of the local template does not match that of
            # the remote template
            funcs.run_repobee(
                f"repos setup -a {TEMPLATE_REPOS_ARG} "
                f"--base-url {platform_url} "
                "--allow-local-templates",
                workdir=template_repo_dir,
            )

        # nothing should have changed, and there should be no errors
        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, funcs.get_repos(platform_url),
        )
        assert "[ERROR]" not in capsys.readouterr().out

    def test_setup_with_local_repos_fails_without_local_templates_arg(
        self, platform_url
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_repo_dir = pathlib.Path(tmpdir)
            task_34 = template_repo_dir / "task-34"
            create_local_repo(task_34, [("somefile.txt", "Yay!")])

            with pytest.raises(exception.ParseError) as exc_info:
                funcs.run_repobee(
                    f"repos setup -a {task_34.name} "
                    f"--base-url {platform_url} ",
                    workdir=template_repo_dir,
                )

            assert "`--allow-local-templates`" in str(exc_info.value)

    def test_use_local_template_with_strangely_named_default_branch(
        self, platform_url
    ):
        """Test setting up student repos with a template repo that has a
        non-standard default branch name. The student repos should get
        the same default branch.
        """
        strange_branch_name = "definitelynotmaster"

        with tempfile.TemporaryDirectory() as tmpdir:
            template_repo_dir = pathlib.Path(tmpdir)
            task_99 = template_repo_dir / "task-99"
            create_local_repo(
                task_99,
                [("README.md", "Read me plz.")],
                default_branch=strange_branch_name,
            )

            funcs.run_repobee(
                f"repos setup -a {task_99.name} "
                f"--base-url {platform_url} "
                "--allow-local-templates",
                workdir=template_repo_dir,
            )

            repo = git.Repo(funcs.get_repos(platform_url)[0].path)

            assert len(repo.branches) == 1
            assert repo.branches[0].name == strange_branch_name

    def test_pre_setup_hook(self, platform_url):
        """Test that the pre-setup hook is run for each template repo."""
        expected_repo_names = set(TEMPLATE_REPO_NAMES)

        class PreSetupPlugin(plug.Plugin):
            def pre_setup(
                self, repo: plug.TemplateRepo, api: plug.PlatformAPI
            ):
                expected_repo_names.remove(repo.name)

                assert isinstance(api, localapi.LocalAPI)
                assert repo.path.exists

        funcs.run_repobee(
            f"repos setup -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            plugins=[PreSetupPlugin],
        )

        assert not expected_repo_names


class TestClone:
    """Tests for the ``repos clone`` command."""

    def test_clone_all_repos(self, platform_url, with_student_repos):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = pathlib.Path(tmp)
            funcs.run_repobee(
                f"repos clone -a {TEMPLATE_REPOS_ARG} "
                f"--base-url {platform_url}",
                workdir=workdir,
            )
            assert_cloned_student_repos_match_templates(
                STUDENT_TEAMS, TEMPLATE_REPO_NAMES, workdir
            )

    def test_clone_discover_repos(self, platform_url, with_student_repos):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = pathlib.Path(tmp)
            funcs.run_repobee(
                f"repos clone --discover-repos " f"--base-url {platform_url} ",
                workdir=workdir,
            )
            assert_cloned_student_repos_match_templates(
                STUDENT_TEAMS, TEMPLATE_REPO_NAMES, workdir
            )

    def test_post_clone_hook_invoked_on_all_student_repos(
        self, platform_url, with_student_repos
    ):
        """Test that the post_clone hook is called with the expected
        repositories.
        """
        expected_repo_names = set(
            plug.generate_repo_names(STUDENT_TEAMS, TEMPLATE_REPO_NAMES)
        )

        class PostClonePlugin(plug.Plugin):
            def post_clone(
                self, repo: plug.StudentRepo, api: plug.PlatformAPI
            ):
                # remove repo names one by one, in the end none should remain
                expected_repo_names.remove(repo.name)

                assert isinstance(api, localapi.LocalAPI)
                assert repo.path.is_dir()

        funcs.run_repobee(
            f"repos clone -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            plugins=[PostClonePlugin],
        )

        assert not expected_repo_names

    def test_javac_plugin_happy_path(self, platform_url, tmp_path_factory):
        workdir = tmp_path_factory.mktemp("workdir")
        java_task = self._setup_task_with_java_code(platform_url, workdir)
        repo_names = plug.generate_repo_names(STUDENT_TEAMS, [java_task.name])

        plug_results = funcs.run_repobee(
            f"repos clone -a {java_task.name} --base-url {platform_url} ",
            plugins=[_repobee.ext.javac],
        )

        assert plug_results
        assert len(plug_results) == len(repo_names)
        for repo_name in repo_names:
            javac_result, *_ = plug_results[repo_name]
            assert javac_result.name == "javac"
            assert javac_result.status == plug.Status.SUCCESS

    def _setup_task_with_java_code(
        self, platform_url, workdir
    ) -> pathlib.Path:
        java_task = workdir / "java-task"
        create_local_repo(java_task, [("src/Main.java", _JAVA_MAIN_CLASS)])
        funcs.run_repobee(
            f"repos setup -a {java_task.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=workdir,
        )
        return java_task


class TestUpdate:
    """Tests for the ``repos update`` command."""

    def test_does_not_create_repos(self, platform_url):
        """This command should only update existing repos, it's not allowed to
        create repos.
        """
        # arrange, must create the student teams
        funcs.run_repobee(f"teams create --base-url {platform_url}")

        # act
        funcs.run_repobee(
            f"repos update -a {TEMPLATE_REPOS_ARG} --base-url {platform_url}"
        )

        # assert
        assert not funcs.get_repos(platform_url)


class TestMigrate:
    """Tests for the ``repos migrate`` command."""

    def test_use_strange_default_branch_name(self, platform_url):
        strange_branch_name = "definitelynotmaster"

        with tempfile.TemporaryDirectory() as tmpdir:
            template_repo_dir = pathlib.Path(tmpdir)
            task_99 = template_repo_dir / "task-99"
            create_local_repo(
                task_99,
                [("README.md", "Read me plz.")],
                default_branch=strange_branch_name,
            )

            funcs.run_repobee(
                f"repos migrate -a {task_99.name} "
                f"--base-url {platform_url} "
                "--allow-local-templates",
                workdir=template_repo_dir,
            )

            platform_repos = funcs.get_repos(platform_url)
            assert len(platform_repos) == 1
            repo = git.Repo(funcs.get_repos(platform_url)[0].path)

            assert len(repo.branches) == 1
            assert repo.branches[0].name == strange_branch_name


def create_local_repo(
    path: pathlib.Path,
    files: Iterable[Tuple[str, str]],
    default_branch: str = "master",
) -> str:
    """Create a local repository in the provided basedir and return a
    hash of the contents.

    Args:
        path: Path to put the repository at. Parent directories are created if
            they don't exist.
        files: Files to add to the repository. Should be tuples on the form
            (relpath, content), where relpath is a filepath relative to the
            root of the repository.
        default_branch: The default branch to use for the repository.
    Returns:
        The sha1 hash of the repository.
    """
    path.mkdir(parents=True)
    for filename, content in files:
        file = path / filename
        file.parent.mkdir(parents=True, exist_ok=True)
        (path / filename).write_text(content, encoding="utf8")
    sha = funcs.hash_directory(path)
    funcs.initialize_repo(path, default_branch)
    return sha


_JAVA_MAIN_CLASS = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, world!");
    }
}
"""
