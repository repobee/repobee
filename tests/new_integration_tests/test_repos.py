"""Tests for the repos category of commands."""
import pathlib
import tempfile

from typing import List, Mapping

import git

import repobee_plug as plug
from repobee_testhelpers import localapi
from repobee_testhelpers import funcs


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

        # arrange
        def reponize(dirpath: pathlib.Path):
            repo = git.Repo.init(dirpath)
            repo.init()
            repo.git.add(".", "--force")
            repo.git.commit("-m", "Initial commit")

        with tempfile.TemporaryDirectory() as tmpdir:
            template_repo_dir = pathlib.Path(tmpdir)
            template_repo_hashes = {}

            task_34_repo = template_repo_dir / "task-34"
            task_34_repo.mkdir()
            task_34_file = task_34_repo / "somefile.txt"
            task_34_file.write_text("This is task 34!", encoding="utf8")
            template_repo_hashes[task_34_repo.name] = funcs.hash_directory(
                task_34_repo
            )
            reponize(task_34_repo)

            task_55_repo = template_repo_dir / "task-55"
            task_55_repo.mkdir()
            task_55_file = task_55_repo / "hello.py"
            task_55_file.write_text("print('hello, world!')", encoding="utf8")
            template_repo_hashes[task_55_repo.name] = funcs.hash_directory(
                task_55_repo
            )
            reponize(task_55_repo)

            # act
            funcs.run_repobee(
                f"repos setup -a {task_55_repo.name} {task_34_repo.name} "
                f"--base-url {platform_url} ",
                workdir=template_repo_dir,
            )

            # assert
            repo_dict = {
                repo.name: repo.path for repo in funcs.get_repos(platform_url)
            }

            _assert_repos_match_templates(
                STUDENT_TEAMS,
                [task_34_repo.name, task_55_repo.name],
                template_repo_hashes,
                repo_dict,
            )

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
