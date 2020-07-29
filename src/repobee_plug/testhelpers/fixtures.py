"""Fixtures for use with pytest."""
import pathlib
import pytest
import shutil

from repobee_plug.testhelpers import funcs

from repobee_plug.testhelpers.const import (
    TEMPLATE_ORG_NAME,
    TEMPLATE_REPO_DIR,
    TEMPLATE_REPOS_ARG,
    STUDENTS_FILE,
    TEACHER,
    TARGET_ORG_NAME,
)


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
        funcs.initialize_repo(template_repo)

    return pathlib.Path(tmpdir)


@pytest.fixture
def platform_url(platform_dir):
    """Base url to the platform."""
    return "https://" + str(platform_dir)


@pytest.fixture
def with_student_repos(platform_url):
    funcs.run_repobee(
        f"repos setup --mn {TEMPLATE_REPOS_ARG} "
        f"--students-file {STUDENTS_FILE} "
        f"--base-url {platform_url} "
        f"--user {TEACHER} "
        f"--org-name {TARGET_ORG_NAME} "
        f"--master-org-name {TEMPLATE_ORG_NAME}"
    )
