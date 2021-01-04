"""Integration test fixtures."""
import os

import gitlab
import pytest
import repobee_plug as plug

from repobee_testhelpers._internal.docker import run_in_docker

import gitlabmanager
import repobee_plug.cli
from _helpers.asserts import (
    assert_repos_exist,
    assert_on_groups,
    assert_num_issues,
    assert_issues_exist,
)
from _helpers.const import (
    REPOBEE_GITLAB,
    BASE_ARGS,
    TEMPLATE_ORG_ARG,
    MASTER_REPOS_ARG,
    STUDENTS_ARG,
    STUDENT_TEAMS,
    assignment_names,
    LOCAL_BASE_URL,
    TOKEN,
    ORG_NAME,
    STUDENT_TEAM_NAMES,
)
from _helpers.helpers import expected_num_members_group_assertion, get_group

assert os.getenv(
    "REPOBEE_NO_VERIFY_SSL"
), "The env variable REPOBEE_NO_VERIFY_SSL must be set to 'true'"


@pytest.fixture(autouse=True, scope="session")
def setup_gitlab_instance():
    """Perform first-time setup of the GitLab instance."""
    gitlabmanager.setup()


@pytest.fixture(autouse=True, scope="session")
def teardown_gitlab_instance():
    """Teardown the GitLab instance after all tests have finished."""
    yield
    gitlabmanager.teardown()


@pytest.fixture(autouse=True)
def restore():
    """Run the script that restores the GitLab instance to its initial
    state.
    """
    gitlabmanager.restore()


@pytest.fixture
def with_student_repos(restore):
    """Set up student repos before starting tests.

    Note that explicitly including restore here is necessary to ensure that
    it runs before this fixture.
    """
    command = " ".join(
        [
            REPOBEE_GITLAB,
            *str(repobee_plug.cli.CoreCommand.repos.setup).split(),
            *BASE_ARGS,
            *TEMPLATE_ORG_ARG,
            *MASTER_REPOS_ARG,
            *STUDENTS_ARG,
        ]
    )

    result = run_in_docker(command)

    # pre-test asserts
    assert result.returncode == 0
    assert_repos_exist(STUDENT_TEAMS, assignment_names)
    assert_on_groups(STUDENT_TEAMS)


@pytest.fixture
def open_issues(with_student_repos):
    """Open two issues in each student repo."""
    task_issue = plug.Issue(
        title="Task", body="The task is to do this, this and that"
    )
    correction_issue = plug.Issue(
        title="Correction required", body="You need to fix this, this and that"
    )
    issues = [task_issue, correction_issue]
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = get_group(ORG_NAME, gl=gl)
    projects = (
        gl.projects.get(p.id)
        for p in target_group.projects.list(include_subgroups=True, all=True)
    )
    for project in projects:
        project.issues.create(
            dict(title=task_issue.title, description=task_issue.body)
        )
        project.issues.create(
            dict(
                title=correction_issue.title, description=correction_issue.body
            )
        )

    assert_num_issues(STUDENT_TEAM_NAMES, assignment_names, len(issues))
    assert_issues_exist(STUDENT_TEAM_NAMES, assignment_names, task_issue)
    assert_issues_exist(STUDENT_TEAM_NAMES, assignment_names, correction_issue)

    return issues


@pytest.fixture
def with_reviews(with_student_repos):
    assignment_name = assignment_names[1]
    expected_review_teams = [
        plug.StudentTeam(
            members=[],
            name=plug.generate_review_team_name(
                student_team_name, assignment_name
            ),
        )
        for student_team_name in STUDENT_TEAM_NAMES
    ]
    command = " ".join(
        [
            REPOBEE_GITLAB,
            *str(repobee_plug.cli.CoreCommand.reviews.assign).split(),
            *BASE_ARGS,
            "-a",
            assignment_name,
            *STUDENTS_ARG,
            "-n",
            "1",
        ]
    )

    result = run_in_docker(command)

    assert result.returncode == 0
    assert_on_groups(
        expected_review_teams,
        single_group_assertion=expected_num_members_group_assertion(1),
    )
    return (assignment_name, expected_review_teams)
