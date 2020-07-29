"""Tests for the repos category of commands."""
import pathlib
import shutil
import tempfile

from typing import List

import git
import pytest

import repobee
import repobee_plug as plug
from repobee_plug.testhelpers import fakeapi

TARGET_ORG_NAME = "fall2020"
TEMPLATE_ORG_NAME = "templates"

CUR_DIR = pathlib.Path(__file__).absolute().parent
TEMPLATE_REPO_DIR = CUR_DIR / "resources" / TEMPLATE_ORG_NAME
TEMPLATE_REPO_NAMES = [
    d.name for d in TEMPLATE_REPO_DIR.iterdir() if d.is_dir()
]
TEMPLATE_REPOS_ARG = " ".join(TEMPLATE_REPO_NAMES)

TEACHER = "ric"
STUDENTS_FILE = CUR_DIR / "resources" / "students.txt"
STUDENT_TEAMS = plug.fileutils.parse_students_file(STUDENTS_FILE)


@pytest.fixture(autouse=True)
def platform_dir(tmpdir):
    """Setup the platform emulation with a template organization with git
    repositories, the students and teacher as users,  and return the the
    workdirectory for the platform.
    """
    template_org_dir = pathlib.Path(tmpdir) / TEMPLATE_ORG_NAME
    shutil.copytree(src=TEMPLATE_REPO_DIR, dst=template_org_dir)
    for template_repo in template_org_dir.iterdir():
        if not template_repo.is_dir():
            continue
        initialize_repo(template_repo)

    return pathlib.Path(tmpdir)


@pytest.fixture
def platform_url(platform_dir):
    """Base url to the platform."""
    return "https://" + str(platform_dir)


@pytest.fixture
def with_student_repos(platform_url):
    run_repobee(
        f"repos setup --mn {TEMPLATE_REPOS_ARG} "
        f"--students-file {STUDENTS_FILE} "
        f"--base-url {platform_url} "
        f"--user {TEACHER} "
        f"--org-name {TARGET_ORG_NAME} "
        f"--master-org-name {TEMPLATE_ORG_NAME}"
    )


def hash_directory(dirpath: pathlib.Path) -> str:
    """Compute the directory hash using Git.

    Args:
        dirpath: Path to a directory.
    Returns:
        The hash of the root tree of the directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = pathlib.Path(tmpdir) / "repo"
        shutil.copytree(dirpath, target_dir)
        repo = initialize_repo(target_dir)
        return repo.head.commit.tree.hexsha


def initialize_repo(path: pathlib.Path) -> git.Repo:
    """Initialize the directory to a Git repo and commit all files in it.
    """
    repo = git.Repo.init(path)
    repo.git.add(".", "--force")
    repo.git.commit("-m", "Initial commit")
    return repo


TEMPLATE_REPO_HASHES = {
    path.name: hash_directory(path)
    for path in map(lambda name: TEMPLATE_REPO_DIR / name, TEMPLATE_REPO_NAMES)
}


def tree_hash(repo_root: pathlib.Path) -> str:
    """Get the hash of the HEAD tree object of this repository.

    Args:
        repo_root: Path to the root of a Git repository.
    Returns:
        The hash of the root tree object.
    """
    repo = git.Repo(repo_root)
    return repo.head.commit.tree.hexsha


def run_repobee(cmd: str, **kwargs):
    """Helper function to call repobee.run.

    Note that ``cmd`` should be a string, and not a list of strings.
    """
    repobee.run(cmd.split(), **kwargs, plugins=[fakeapi])


def assert_student_repos_match_templates(
    student_teams: List[plug.Team],
    template_repo_names: List[str],
    student_repo_dir: pathlib.Path,
):
    """Assert that the content of the student repos matches the content of the
    respective template repos.
    """
    expected_repo_asserts = len(student_teams) * len(template_repo_names)
    actual_repo_asserts = 0

    for template_name in template_repo_names:
        student_repos = [
            student_repo_dir / repo_name
            for repo_name in plug.generate_repo_names(
                student_teams, [template_name]
            )
        ]
        assert len(student_repos) == len(student_teams)
        for repo in student_repos:
            actual_repo_asserts += 1
            assert tree_hash(repo) == TEMPLATE_REPO_HASHES[template_name]

    assert (
        expected_repo_asserts == actual_repo_asserts
    ), "Performed fewer asserts than expected"


class TestSetup:
    """Tests for the ``repos setup`` command."""

    def test_setup_single_template_repo(self, platform_dir, platform_url):
        template_repo_name = TEMPLATE_REPO_NAMES[0]
        run_repobee(
            f"repos setup --mn {template_repo_name} "
            f"--students-file {STUDENTS_FILE} "
            f"--base-url {platform_url} "
            f"--user {TEACHER} "
            f"--org-name {TARGET_ORG_NAME} "
            f"--master-org-name {TEMPLATE_ORG_NAME}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, [template_repo_name], platform_dir / TARGET_ORG_NAME
        )

    def test_setup_multiple_template_repos(self, platform_dir, platform_url):
        run_repobee(
            f"repos setup --mn {TEMPLATE_REPOS_ARG} "
            f"--students-file {STUDENTS_FILE} "
            f"--base-url {platform_url} "
            f"--user {TEACHER} "
            f"--org-name {TARGET_ORG_NAME} "
            f"--master-org-name {TEMPLATE_ORG_NAME}"
        )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, platform_dir / TARGET_ORG_NAME
        )

    def test_setup_multiple_template_repos_twice(
        self, platform_dir, platform_url
    ):
        """Running setup command twice should have the same effect as running
        it once.
        """
        for _ in range(2):
            run_repobee(
                f"repos setup --mn {TEMPLATE_REPOS_ARG} "
                f"--students-file {STUDENTS_FILE} "
                f"--base-url {platform_url} "
                f"--user {TEACHER} "
                f"--org-name {TARGET_ORG_NAME} "
                f"--master-org-name {TEMPLATE_ORG_NAME}"
            )

        assert_student_repos_match_templates(
            STUDENT_TEAMS, TEMPLATE_REPO_NAMES, platform_dir / TARGET_ORG_NAME
        )


class TestClone:
    """Tests for the ``repos clone`` command."""

    def test_clone_all_repos(self, platform_url, with_student_repos):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = pathlib.Path(tmp)
            run_repobee(
                f"repos clone --mn {TEMPLATE_REPOS_ARG} "
                f"--students-file {STUDENTS_FILE} "
                f"--base-url {platform_url} "
                f"--user {TEACHER} "
                f"--org-name {TARGET_ORG_NAME} ",
                workdir=workdir,
            )
            assert_student_repos_match_templates(
                STUDENT_TEAMS, TEMPLATE_REPO_NAMES, workdir
            )
