import pathlib
import os
import secrets

import pytest
import gitlabmanager

import _repobee.cli.mainparser

import asserts
from helpers import *

assert os.getenv(
    "REPOBEE_NO_VERIFY_SSL"
), "The env variable REPOBEE_NO_VERIFY_SSL must be set to 'true'"


@pytest.fixture
def base_args(target_group_name):
    return [
        "--bu",
        BASE_URL,
        "-o",
        target_group_name,
        "-t",
        TOKEN,
    ]


@pytest.fixture
def target_group_name(create_groups):
    target_name, _ = create_groups
    return target_name


@pytest.fixture
def master_group_name(create_groups):
    _, master_name = create_groups
    return master_name


@pytest.fixture
def master_org_arg(master_group_name):
    return ["--mo", master_group_name]


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
def create_groups():
    """Create a new target group for this test run."""
    group_suffix = secrets.token_hex(5)
    target_group_name = f"dd1337-{group_suffix}"
    master_group_name = f"dd1337-master-{group_suffix}"
    gitlabmanager.create_groups_and_projects(
        course_round_group_name=target_group_name,
        master_group_name=master_group_name,
    )
    return target_group_name, master_group_name


@pytest.fixture
def tmpdir_volume_arg(tmpdir):
    """Create a temporary directory and return an argument string that
    will mount a docker volume to it.
    """
    yield "-v {}:{}".format(str(tmpdir), VOLUME_DST)


@pytest.fixture(scope="module", autouse=True)
def coverage_volume():
    covdir = pathlib.Path(".").resolve() / ".coverage_files"
    yield "-v {}:{}".format(str(covdir), COVERAGE_VOLUME_DST)
    covfile = covdir / ".coverage"
    assert covfile.is_file()


@pytest.fixture(scope="module", autouse=True)
def generate_coverage_report(coverage_volume):
    """Generate a coverage report after all tests have run."""
    yield
    # xml report for Codecov
    run_in_docker(
        "cd {} && coverage xml".format(COVERAGE_VOLUME_DST),
        extra_args=[coverage_volume],
    )
    # txt report for manual inspection
    run_in_docker(
        "cd {} && coverage report > report.txt".format(COVERAGE_VOLUME_DST),
        extra_args=[coverage_volume],
    )


@pytest.fixture(autouse=True)
def handle_coverage_file(extra_args):
    """Copy the coverage file back and forth."""
    # copy the previous .coverage file into the workdir
    run_in_docker(
        "cp {}/.coverage .".format(COVERAGE_VOLUME_DST), extra_args=extra_args
    )
    yield
    # copy the appended .coverage file into the coverage volume
    run_in_docker(
        "cp .coverage {}".format(COVERAGE_VOLUME_DST), extra_args=extra_args
    )


@pytest.fixture
def extra_args(tmpdir_volume_arg, coverage_volume):
    """Extra arguments to pass to run_in_docker when executing a test."""
    return [tmpdir_volume_arg, coverage_volume]


@pytest.fixture
def with_student_repos(base_args, master_org_arg, target_group_name):
    """Set up student repos before starting tests"""
    command = " ".join(
        [
            REPOBEE_GITLAB,
            _repobee.cli.mainparser.SETUP_PARSER,
            *base_args,
            *master_org_arg,
            *MASTER_REPOS_ARG,
            *STUDENTS_ARG,
        ]
    )

    result = run_in_docker(command)

    # pre-test asserts
    assert result.returncode == 0
    asserts.assert_repos_exist(
        STUDENT_TEAMS, MASTER_REPO_NAMES, org_name=target_group_name
    )
    asserts.assert_on_groups(STUDENT_TEAMS, target_group_name)


@pytest.fixture
def open_issues(with_student_repos, create_groups):
    """Open two issues in each student repo."""
    target_group_name, _ = create_groups
    task_issue = plug.Issue(
        title="Task", body="The task is to do this, this and that"
    )
    correction_issue = plug.Issue(
        title="Correction required", body="You need to fix this, this and that"
    )
    issues = [task_issue, correction_issue]
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=target_group_name)[0]
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

    asserts.assert_num_issues(
        STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, len(issues)
    )
    asserts.assert_issues_exist(
        STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, task_issue
    )
    asserts.assert_issues_exist(
        STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, correction_issue
    )

    return issues
