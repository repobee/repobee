"""Tests for the repos category of commands."""
import pathlib
import itertools
import shutil

from typing import List, Mapping, Tuple, Iterable

import git
import pytest

import _repobee.ext.javac
import _repobee.ext.pylint

import repobee_plug as plug
from repobee_testhelpers import localapi
from repobee_testhelpers import funcs
from _repobee import exception


from repobee_testhelpers import const
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

    def test_setup_multiple_template_repos_quietly(
        self, platform_dir, platform_url, capsys
    ):
        """Run with `-q` and there should be no output."""
        funcs.run_repobee(
            f"repos setup -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            "-q"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, funcs.get_repos(platform_url)
        )
        out_err = capsys.readouterr()
        assert not out_err.out.strip()
        assert not out_err.err.strip()

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

    def test_setup_with_local_repos(self, platform_url, tmp_path):
        """Test running the setup command with the names of local
        repositories. That is to say, repos that are not in the
        template organization.
        """
        # arrange
        template_repo_hashes = {}

        task_34 = tmp_path / "task-34"
        task_55 = tmp_path / "task-55"
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
            workdir=tmp_path,
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
        self, platform_url, with_student_repos, capsys, tmp_path
    ):
        """This command should not push to existing repos, that's for the
        ``update`` command to do.
        """
        # arrange
        task = tmp_path / TEMPLATE_REPO_NAMES[0]
        create_local_repo(task, [("best/file/ever.txt", "content")])

        # act
        # this push would fail if it was attempted, as the repo
        # content of the local template does not match that of
        # the remote template
        funcs.run_repobee(
            f"repos setup -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
        )

        # nothing should have changed, and there should be no errors
        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, funcs.get_repos(platform_url)
        )
        assert "[ERROR]" not in capsys.readouterr().out

    def test_setup_with_local_repos_fails_without_local_templates_arg(
        self, platform_url, tmp_path
    ):
        task_34 = tmp_path / "task-34"
        create_local_repo(task_34, [("somefile.txt", "Yay!")])

        with pytest.raises(exception.ParseError) as exc_info:
            funcs.run_repobee(
                f"repos setup -a {task_34.name} "
                f"--base-url {platform_url} ",
                workdir=tmp_path,
            )

        assert "`--allow-local-templates`" in str(exc_info.value)

    def test_use_local_template_with_strangely_named_default_branch(
        self, platform_url, tmp_path
    ):
        """Test setting up student repos with a template repo that has a
        non-standard default branch name. The student repos should get
        the same default branch.
        """
        strange_branch_name = "definitelynotmaster"
        task_99 = tmp_path / "task-99"
        create_local_repo(
            task_99,
            [("README.md", "Read me plz.")],
            default_branch=strange_branch_name,
        )

        funcs.run_repobee(
            f"repos setup -a {task_99.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
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

    def test_use_non_standard_repo_names(self, platform_url):
        """Test setting up repos with non-standard repo names using an
        implementation of the ``generate_repo_name`` hook.
        """

        def generate_repo_name(team_name, assignment_name):
            return f"{assignment_name}-BONKERS-{team_name}"

        expected_repo_names = [
            generate_repo_name(team, assignment_name)
            for team, assignment_name in itertools.product(
                const.STUDENT_TEAMS, const.TEMPLATE_REPO_NAMES
            )
        ]

        class StrangeNamingConvention(plug.Plugin):
            def generate_repo_name(self, team_name, assignment_name):
                return generate_repo_name(team_name, assignment_name)

        funcs.run_repobee(
            f"repos setup -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            plugins=[StrangeNamingConvention],
        )

        actual_repo_names = [
            repo.name for repo in funcs.get_repos(platform_url)
        ]
        assert sorted(actual_repo_names) == sorted(expected_repo_names)


class TestClone:
    """Tests for the ``repos clone`` command."""

    def test_clone_all_repos(self, platform_url, with_student_repos, tmp_path):
        funcs.run_repobee(
            f"repos clone -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            workdir=tmp_path,
        )
        assert_cloned_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, tmp_path
        )

    def test_clone_local_gitconfig(
        self, platform_url, with_student_repos, tmp_path
    ):
        funcs.run_repobee(
            f"repos clone --assignments {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            workdir=tmp_path,
        )

        # do a spot check on a single repo
        team = STUDENT_TEAMS[0]
        assignment_name = TEMPLATE_REPO_NAMES[0]
        repo = git.Repo(
            tmp_path
            / str(team)
            / plug.generate_repo_name(team, assignment_name)
        )
        assert "pull.ff=only" in repo.git.config("--local", "--list")

    def test_use_non_standard_repo_names(self, platform_url, tmp_path):
        """Test cloning repos with non-standard repo names using an
        implementation of the ``generate_repo_name`` hook.
        """
        # arrange
        def generate_repo_name(team_name, assignment_name):
            return f"{assignment_name}-BONKERS-{team_name}"

        class StrangeNamingConvention(plug.Plugin):
            def generate_repo_name(self, team_name, assignment_name):
                return generate_repo_name(team_name, assignment_name)

        expected_repo_names = [
            generate_repo_name(team, assignment_name)
            for team, assignment_name in itertools.product(
                const.STUDENT_TEAMS, const.TEMPLATE_REPO_NAMES
            )
        ]
        funcs.run_repobee(
            f"repos setup -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            plugins=[StrangeNamingConvention],
        )

        # act
        funcs.run_repobee(
            f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            workdir=tmp_path,
            plugins=[StrangeNamingConvention],
        )

        # assert
        local_repos = itertools.chain.from_iterable(
            student_dir.iterdir() for student_dir in tmp_path.iterdir()
        )
        actual_repo_names = [
            repo_path.name for repo_path in local_repos if repo_path.is_dir()
        ]
        assert sorted(actual_repo_names) == sorted(expected_repo_names)

    def test_clone_discover_repos(
        self, platform_url, with_student_repos, tmp_path
    ):
        funcs.run_repobee(
            f"repos clone --discover-repos " f"--base-url {platform_url} ",
            workdir=tmp_path,
        )
        assert_cloned_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, tmp_path
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

    def test_javac_plugin_happy_path(self, platform_url, tmp_path):
        java_task = self._setup_task_with_java_code(platform_url, tmp_path)
        repo_names = plug.generate_repo_names(STUDENT_TEAMS, [java_task.name])

        plug_results = funcs.run_repobee(
            f"repos clone -a {java_task.name} --base-url {platform_url} ",
            plugins=[_repobee.ext.javac],
            workdir=tmp_path,
        )

        assert plug_results
        assert len(plug_results) == len(repo_names)
        for repo_name in repo_names:
            javac_result, *_ = plug_results[repo_name]
            assert javac_result.name == "javac"
            assert javac_result.status == plug.Status.SUCCESS

    def test_pylint_plugin_happy_path(self, platform_url, tmp_path):
        python_task = self._setup_task_with_python_code(platform_url, tmp_path)
        repo_names = plug.generate_repo_names(
            STUDENT_TEAMS, [python_task.name]
        )

        plug_results = funcs.run_repobee(
            f"repos clone -a {python_task.name} --base-url {platform_url}",
            plugins=[_repobee.ext.pylint],
            workdir=tmp_path,
        )

        assert plug_results
        assert len(plug_results) == len(repo_names)
        for repo_name in repo_names:
            pylint_result, *_ = plug_results[repo_name]
            assert pylint_result.name == "pylint"
            assert pylint_result.status == plug.Status.SUCCESS
            assert "src/main.py -- OK" in pylint_result.msg

    def test_pylint_plugin_with_python_syntax_error(
        self, platform_url, tmp_path
    ):
        """Test that the pylint plugin correctly reports errors."""
        python_task = self._setup_task_with_faulty_python_code(
            platform_url, tmp_path
        )
        repo_names = plug.generate_repo_names(
            STUDENT_TEAMS, [python_task.name]
        )

        plug_results = funcs.run_repobee(
            f"repos clone -a {python_task.name} --base-url {platform_url}",
            plugins=[_repobee.ext.pylint],
            workdir=tmp_path,
        )

        assert plug_results
        assert len(plug_results) == len(repo_names)
        for repo_name in repo_names:
            pylint_result, *_ = plug_results[repo_name]
            assert pylint_result.name == "pylint"
            assert pylint_result.status == plug.Status.ERROR
            assert "src/main.py -- ERROR" in pylint_result.msg

    def _setup_task_with_faulty_python_code(self, platform_url, tmp_path):
        python_task = tmp_path / "python-task"
        python_code = (
            "print('Hello, world!'"  # note missing closing parenthesis
        )
        create_local_repo(python_task, [("src/main.py", python_code)])
        funcs.run_repobee(
            f"repos setup -a {python_task.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
        )
        return python_task

    def _setup_task_with_python_code(self, platform_url, tmp_path):
        python_task = tmp_path / "python-task"
        python_code = "print('Hello, world!')"
        create_local_repo(python_task, [("src/main.py", python_code)])
        funcs.run_repobee(
            f"repos setup -a {python_task.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
        )
        return python_task

    def _setup_task_with_java_code(
        self, platform_url, tmp_path
    ) -> pathlib.Path:
        java_task = tmp_path / "java-task"
        create_local_repo(java_task, [("src/Main.java", _JAVA_MAIN_CLASS)])
        funcs.run_repobee(
            f"repos setup -a {java_task.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
        )
        return java_task

    def test_clone_all_repos_quietly(
        self, platform_url, with_student_repos, capsys, tmp_path
    ):
        """Try cloning repos with `-q` for the most quiet of experiences."""
        funcs.run_repobee(
            f"repos clone -a {TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            "-q",
            workdir=tmp_path,
        )
        assert_cloned_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, tmp_path
        )

        out_err = capsys.readouterr()
        assert not out_err.out.strip()
        assert not out_err.err.strip()

    def test_clone_non_existing_repos_with_errors_silenced_is_quiet(
        self, platform_url, capsys
    ):
        """Cloning repos that don't exist with `-qqq` should silence all
        errors.
        """
        funcs.run_repobee(
            f"repos clone -a {TEMPLATE_REPOS_ARG} --base-url {platform_url} "
            "-qqq"
        )

        out_err = capsys.readouterr()
        assert not out_err.out.strip()
        assert not out_err.err.strip()

    def test_clone_non_existing_repos_repos_with_warnings_silenced(
        self, platform_url, capsys
    ):
        """Cloning repos that don't exist with `-qq` should still yield
        errors.
        """
        funcs.run_repobee(
            f"repos clone -a task-999 task-task --base-url {platform_url} -qq"
        )

        out_err = capsys.readouterr()
        assert not out_err.out.strip()
        assert "[ERROR]" in out_err.err.strip()

    def test_clone_twice_with_warnings_silenced(
        self, with_student_repos, platform_url, capsys, tmp_path
    ):
        """Cloning the same repos twice with `-qq` should prevent warnings
        about repos already existing from showing up.
        """
        for _ in range(2):
            funcs.run_repobee(
                f"repos clone -a {TEMPLATE_REPOS_ARG} "
                f"--base-url {platform_url} "
                "-qq",
                workdir=tmp_path,
            )

        assert_cloned_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, tmp_path
        )
        out_err = capsys.readouterr()
        assert not out_err.out.strip()
        assert not out_err.err.strip()

    def test_empty_student_repos_dont_cause_errors(
        self, with_student_repos, platform_url, capsys, tmp_path
    ):
        """No error messages should be displayed when empty repos are
        cloned, and the empty repos should be on disk.
        """
        # arrange
        task_name = self._setup_empty_task(platform_url)

        # act
        funcs.run_repobee(
            f"repos clone -a {task_name} --base-url {platform_url} ",
            workdir=tmp_path,
        )

        # assert
        assert not capsys.readouterr().err
        for student_team in STUDENT_TEAMS:
            repo = (
                tmp_path
                / student_team.name
                / plug.generate_repo_name(student_team.name, task_name)
            )
            assert repo.is_dir()
            assert [f.name for f in repo.iterdir()] == [".git"]

    def _setup_empty_task(self, platform_url: str) -> str:
        task_name = "empty-task"
        api = funcs.get_api(platform_url)
        for team in api.get_teams([t.name for t in STUDENT_TEAMS]):
            repo_name = plug.generate_repo_name(team.name, task_name)
            api.create_repo(
                name=repo_name,
                description="An empty task",
                private=True,
                team=team,
            )

        return task_name

    def test_update_local(self, platform_url, with_student_repos, tmp_path):
        """Test cloning an updated repository that already exists locally, when
        there are no incompatible changes between the remote copy and the local
        copy and --update-local is specified.
        """
        # arrange
        new_file_name = "suspicious_file.txt"
        target_repo = funcs.get_repos(platform_url)[-1]
        self._clone_all_student_repos(platform_url, tmp_path)

        with funcs.update_repository(target_repo.url) as repo_path:
            (repo_path / new_file_name).write_text(new_file_name)

        # act
        funcs.run_repobee(
            f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
            f"--update-local "
            f"--base-url {platform_url}",
            workdir=tmp_path,
        )

        # assert
        local_repo_path = list(tmp_path.rglob(target_repo.name))[0]
        assert local_repo_path.parent.parent == tmp_path
        local_new_file = local_repo_path / new_file_name
        assert local_new_file.is_file()
        assert local_new_file.read_text() == new_file_name

    def test_update_local_stashes_local_changes(
        self, platform_url, with_student_repos, tmp_path
    ):
        """Test that updating local repositories with unstaged changes causes
        the changes to be stashed, and the update to proceed.
        """
        new_file_name = "suspicious_file.txt"
        target_repo = funcs.get_repos(platform_url)[-1]
        self._clone_all_student_repos(platform_url, tmp_path)

        # update remote repo
        with funcs.update_repository(target_repo.url) as repo_path:
            (repo_path / new_file_name).write_text(new_file_name)
        # update local repo
        local_repo_path = list(tmp_path.rglob(target_repo.name))[0]
        next(
            file for file in local_repo_path.iterdir() if file.is_file()
        ).write_text("this is an update!")

        # act
        funcs.run_repobee(
            f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
            f"--update-local "
            f"--base-url {platform_url}",
            workdir=tmp_path,
        )

        # assert
        assert local_repo_path.parent.parent == tmp_path
        local_new_file = local_repo_path / new_file_name
        assert local_new_file.is_file()
        assert local_new_file.read_text() == new_file_name
        assert git.Repo(local_repo_path).git.stash("list")

    def test_does_not_update_local_by_default(
        self, platform_url, with_student_repos, tmp_path, capsys
    ):
        """Test that cloning an update repository that exists locally does not
        cause it to be updated by default.
        """
        # arrange
        new_file_name = "suspicious_file.txt"
        target_repo = funcs.get_repos(platform_url)[-1]
        self._clone_all_student_repos(platform_url, tmp_path)

        with funcs.update_repository(target_repo.url) as repo_path:
            (repo_path / new_file_name).write_text(new_file_name)

        # act
        funcs.run_repobee(
            f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url}",
            workdir=tmp_path,
        )

        # assert
        local_repo_path = list(tmp_path.rglob(target_repo.name))[0]
        local_new_file = local_repo_path / new_file_name
        assert not local_new_file.is_file()
        assert "--update-local" in capsys.readouterr().err

    def test_raises_on_path_clash_with_non_git_directory(
        self, platform_url, tmp_path, with_student_repos
    ):
        """Test that an error is raised if there is a path clash between a
        student repository and a non-git directory.
        """
        # arrange
        self._clone_all_student_repos(platform_url, tmp_path)
        non_git_dir = (
            tmp_path
            / str(STUDENT_TEAMS[0])
            / plug.generate_repo_name(STUDENT_TEAMS[0], TEMPLATE_REPO_NAMES[0])
        )
        shutil.rmtree(non_git_dir / ".git")

        # act/assert
        with pytest.raises(exception.RepoBeeException) as exc_info:
            funcs.run_repobee(
                f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
                f"--base-url {platform_url}",
                workdir=tmp_path,
            )

        assert (
            f"name clash with directory that is not a Git repository: "
            f"'{non_git_dir}'" in str(exc_info)
        )

    @staticmethod
    def _clone_all_student_repos(
        platform_url: str, tmp_path: pathlib.Path
    ) -> None:
        funcs.run_repobee(
            f"repos clone -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} ",
            workdir=tmp_path,
        )
        assert list(tmp_path.iterdir())


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

    def test_opens_issue_when_push_fails(
        self, platform_url, with_student_repos, tmp_path
    ):
        """Test running update when a student repo has been modified such that
        the push is rejected. The specified issues should then be opened in
        that student's repo, but not in any of the others.
        """
        # arrange
        title = "You done goofed"
        body = "You need to fix these things manually."
        issue_path = tmp_path / "issue.md"
        issue_path.write_text(f"{title}\n{body}", encoding="utf8")

        # modify a student repo
        repo_path = tmp_path / "repo"
        selected_repo = funcs.get_repos(platform_url)[0]
        repo = git.Repo.clone_from(selected_repo.path, to_path=repo_path)
        repo.git.commit("--amend", "-m", "Best commit")
        repo.git.push("--force")

        # act
        funcs.run_repobee(
            f"repos update -a {const.TEMPLATE_REPOS_ARG} "
            f"--base-url {platform_url} "
            f"--issue {issue_path}"
        )

        # assert
        for platform_repo in funcs.get_repos(platform_url):
            if platform_repo.name == selected_repo.name:
                assert len(platform_repo.issues) == 1
                issue = platform_repo.issues[0]
                assert issue.title == title
                assert issue.body == body
            else:
                assert not platform_repo.issues


class TestMigrate:
    """Tests for the ``repos migrate`` command."""

    def test_use_strange_default_branch_name(self, platform_url, tmp_path):
        strange_branch_name = "definitelynotmaster"
        task_99 = tmp_path / "task-99"
        create_local_repo(
            task_99,
            [("README.md", "Read me plz.")],
            default_branch=strange_branch_name,
        )

        funcs.run_repobee(
            f"repos migrate -a {task_99.name} "
            f"--base-url {platform_url} "
            "--allow-local-templates",
            workdir=tmp_path,
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
