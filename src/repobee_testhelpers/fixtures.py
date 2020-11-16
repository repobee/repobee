"""Fixtures for use with pytest."""
import itertools
import pathlib
import pytest
import shutil
import tempfile

from repobee_testhelpers import funcs

from repobee_testhelpers.const import (
    STUDENTS_FILE,
    STUDENT_TEAMS,
    TARGET_ORG_NAME,
    TEACHER,
    TEMPLATE_ORG_NAME,
    TEMPLATE_REPOS_ARG,
    TEMPLATE_REPO_DIR,
)


@pytest.fixture
def platform_dir():
    """Setup the platform emulation with a template organization with git
    repositories, the students and teacher as users,  and return the the
    workdirectory for the platform.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        template_org_dir = pathlib.Path(tmpdir) / TEMPLATE_ORG_NAME
        shutil.copytree(src=TEMPLATE_REPO_DIR, dst=template_org_dir)
        for template_repo in template_org_dir.iterdir():
            if not template_repo.is_dir():
                continue
            funcs.initialize_repo(template_repo)

        api = funcs.get_api("https://" + str(tmpdir))
        api._add_users(
            itertools.chain.from_iterable([t.members for t in STUDENT_TEAMS])
        )

        yield pathlib.Path(tmpdir)


@pytest.fixture
def platform_url(platform_dir):
    """Base url to the platform."""
    return "https://" + str(platform_dir)


@pytest.fixture
def with_student_repos(platform_url):
    funcs.run_repobee(
        f"repos setup -a {TEMPLATE_REPOS_ARG} "
        f"--students-file {STUDENTS_FILE} "
        f"--base-url {platform_url} "
        f"--user {TEACHER} "
        f"--org-name {TARGET_ORG_NAME} "
        f"--template-org-name {TEMPLATE_ORG_NAME}"
    )
