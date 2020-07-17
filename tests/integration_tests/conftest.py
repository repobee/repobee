"""Integration test fixtures."""
import os
import pathlib

import _repobee.cli
import gitlab
import pytest
import repobee_plug as plug

import gitlabmanager
from _helpers.asserts import (
    assert_repos_exist,
    assert_on_groups,
    assert_num_issues,
    assert_issues_exist,
)
from _helpers.const import (
    VOLUME_DST,
    COVERAGE_VOLUME_DST,
    REPOBEE_GITLAB,
    BASE_ARGS,
    MASTER_ORG_ARG,
    MASTER_REPOS_ARG,
    STUDENTS_ARG,
    STUDENT_TEAMS,
    MASTER_REPO_NAMES,
    LOCAL_BASE_URL,
    TOKEN,
    ORG_NAME,
    STUDENT_TEAM_NAMES,
)
from _helpers.helpers import (
    run_in_docker,
    expected_num_members_group_assertion,
)

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
def with_student_repos(restore):
    """Set up student repos before starting tests.

    Note that explicitly including restore here is necessary to ensure that
    it runs before this fixture.
    """
    command = " ".join(
        [
            REPOBEE_GITLAB,
            plug.ParserCategory.REPOS.value,
            _repobee.cli.mainparser.SETUP_PARSER,
            *BASE_ARGS,
            *MASTER_ORG_ARG,
            *MASTER_REPOS_ARG,
            *STUDENTS_ARG,
        ]
    )

    result = run_in_docker(command)

    # pre-test asserts
    assert result.returncode == 0
    assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
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
    target_group = gl.groups.list(search=ORG_NAME)[0]
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

    assert_num_issues(STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, len(issues))
    assert_issues_exist(STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, task_issue)
    assert_issues_exist(
        STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, correction_issue
    )

    return issues


@pytest.fixture
def with_reviews(with_student_repos):
    master_repo_name = MASTER_REPO_NAMES[1]
    expected_review_teams = [
        plug.Team(
            members=[],
            name=plug.generate_review_team_name(
                student_team_name, master_repo_name
            ),
        )
        for student_team_name in STUDENT_TEAM_NAMES
    ]
    command = " ".join(
        [
            REPOBEE_GITLAB,
            plug.ParserCategory.REVIEWS.value,
            _repobee.cli.mainparser.ASSIGN_REVIEWS_PARSER,
            *BASE_ARGS,
            "--mn",
            master_repo_name,
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
    return (master_repo_name, expected_review_teams)
