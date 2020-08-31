"""Tests for the repos category of commands."""
import pathlib
import tempfile

from typing import List, Mapping, Tuple, Iterable

import git
import pytest

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


def reponize(dirpath: pathlib.Path):
    """Turn a non-empty directory into a Git repo and commit all content."""
    repo = git.Repo.init(dirpath)
    repo.init()
    repo.git.add(".", "--force")
    repo.git.commit("-m", "Initial commit")


def create_local_repo(
    path: pathlib.Path, files: Iterable[Tuple[str, str]]
) -> str:
    """Create a local repository in the provided basedir and return a
    hash of the contents.
    """
    path.mkdir()
    for filename, content in files:
        file = path / filename
        file.parent.mkdir(parents=True, exist_ok=True)
        (path / filename).write_text(content, encoding="utf8")
    sha = funcs.hash_directory(path)
    reponize(path)
    return sha
