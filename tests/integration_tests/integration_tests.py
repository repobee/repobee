import subprocess
import pathlib

import pytest
import gitlab

from repobee import util
from repobee import apimeta


DIR = pathlib.Path(__file__).resolve().parent
TOKEN = (DIR / "token").read_text(encoding="utf-8").strip()
RESTORE_SH = DIR / "restore.sh"

OAUTH_USER = "oauth2"
BASE_URL = "https://gitlab.integrationtest.local"
LOCAL_BASE_URL = "https://localhost:50443"
ORG_NAME = "repobee-testing"
MASTER_ORG_NAME = "repobee-master"
ACTUAL_USER = "repobee-user"

MASTER_REPO_NAMES = "task-1 task-2 task-3".split()
STUDENT_TEAMS = [apimeta.Team(members=[s]) for s in "slarse rjglasse".split()]
STUDENT_TEAM_NAMES = [str(t) for t in STUDENT_TEAMS]


def assert_repos_exist(student_teams, master_repo_names, org_name=ORG_NAME):
    """Assert that the associated student repos exist."""

    repo_names = util.generate_repo_names(student_teams, master_repo_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    student_groups = gl.groups.list(id=target_group.id)

    projects = [p for g in student_groups for p in g.projects.list()]
    project_names = [p.name for p in projects]

    assert set(project_names) == set(repo_names)


def assert_groups_exist(student_teams, org_name=ORG_NAME):
    """Assert that the expected student groups exist and that the expected
    members are in them.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    sorted_teams = sorted(list(student_teams), key=lambda t: t.name)

    sorted_groups = sorted(
        list(gl.groups.list(id=target_group.id)), key=lambda g: g.name
    )
    assert set(g.name for g in sorted_groups) == set(
        str(team) for team in sorted_teams
    )
    for group, team in zip(sorted_groups, sorted_teams):
        # the user who owns the OAUTH token is always listed as a member
        # of groups he/she creates
        expected_members = sorted(team.members + [ACTUAL_USER])
        actual_members = sorted(m.username for m in group.members.list())

        assert group.name == team.name
        assert actual_members == expected_members


@pytest.fixture(autouse=True)
def restore():
    subprocess.run(str(RESTORE_SH), shell=True)


def run_in_docker(command):
    docker_command = (
        "docker run --net development --rm --name repobee "
        "repobee:test /bin/sh -c '{}'"
    ).format(command)
    return subprocess.run(docker_command, shell=True)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestSetup:
    """Integration tests for the setup command."""

    def test_clean_setup(self):
        """Test a first-time setup with master repos in the master org."""
        command = (
            "repobee setup -u {} -g {} -o {} -mo {} -mn {} -s {} -t {} -tb"
        ).format(
            OAUTH_USER,
            BASE_URL,
            ORG_NAME,
            MASTER_ORG_NAME,
            " ".join(MASTER_REPO_NAMES),
            " ".join(STUDENT_TEAM_NAMES),
            TOKEN,
        )

        result = run_in_docker(command)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_groups_exist(STUDENT_TEAMS)

    def test_setup_twice(self):
        """Setting up twice should have the same effect as setting up once."""
        command = (
            "repobee setup -u {} -g {} -o {} -mo {} -mn {} -s {} -t {} -tb"
        ).format(
            OAUTH_USER,
            BASE_URL,
            ORG_NAME,
            MASTER_ORG_NAME,
            " ".join(MASTER_REPO_NAMES),
            " ".join(STUDENT_TEAM_NAMES),
            TOKEN,
        )

        result = run_in_docker(command)
        result = run_in_docker(command)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_groups_exist(STUDENT_TEAMS)
