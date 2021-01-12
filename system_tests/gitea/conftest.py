import re
import shlex

import pytest
import giteamanager

import repobee
from _repobee.ext import gitea
from repobee_testhelpers._internal import templates as template_helpers


@pytest.fixture(autouse=True)
def setup_gitea(teardown_gitea):
    giteamanager.setup()


@pytest.fixture(autouse=True)
def teardown_gitea():
    if giteamanager.gitea_is_running():
        giteamanager.teardown()


@pytest.fixture(autouse=True, scope="session")
def teardown_after():
    yield
    giteamanager.teardown()


@pytest.fixture
def with_student_repos():
    command = re.sub(
        r"\s+",
        " ",
        f"""
repos setup --bu https://localhost:3000/api/v1
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --template-org-name {giteamanager.TEMPLATE_ORG_NAME}
    --students {' '.join([t.members[0] for t in giteamanager.STUDENT_TEAMS])}
    --assignments {' '.join(template_helpers.TEMPLATE_REPO_NAMES)}
    --tb
""",
    )

    repobee.run(shlex.split(command), plugins=[gitea])


@pytest.fixture
def target_api():
    return gitea.GiteaAPI(
        giteamanager.API_URL,
        giteamanager.TEACHER_USER,
        giteamanager.TEACHER_TOKEN,
        giteamanager.TARGET_ORG_NAME,
    )


@pytest.fixture
def template_api():
    return gitea.GiteaAPI(
        giteamanager.API_URL,
        giteamanager.TEACHER_USER,
        giteamanager.TEACHER_TOKEN,
        giteamanager.TEMPLATE_ORG_NAME,
    )
