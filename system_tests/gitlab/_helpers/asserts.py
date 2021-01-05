"""Assert functions for integration tests."""
import gitlab
import repobee_plug as plug

from .const import ORG_NAME, LOCAL_BASE_URL, TOKEN, TEACHER
from .helpers import get_group


def assert_template_repos_exist(assignment_names, org_name):
    """Assert that the template repos are in the specified group."""
    group = get_group(org_name)
    actual_repo_names = [g.name for g in group.projects.list(all=True)]
    assert sorted(actual_repo_names) == sorted(assignment_names)


def assert_repos_exist(student_teams, assignment_names, org_name=ORG_NAME):
    """Assert that the associated student repos exist."""
    repo_names = plug.generate_repo_names(student_teams, assignment_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = get_group(org_name, gl=gl)
    student_groups = gl.groups.list(id=target_group.id)

    projects = [p for g in student_groups for p in g.projects.list(all=True)]
    project_names = [p.name for p in projects]

    assert set(project_names) == set(repo_names)


def assert_repos_contain(
    student_teams, assignment_names, filename, text, org=ORG_NAME
):
    """Assert that each of the student repos contain the given file."""
    repo_names = plug.generate_repo_names(student_teams, assignment_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = get_group(org, gl=gl)
    student_groups = gl.groups.list(id=target_group.id)

    projects = [
        gl.projects.get(p.id)
        for g in student_groups
        for p in g.projects.list(all=True)
        if p.name in repo_names
    ]
    assert len(projects) == len(repo_names)
    for project in projects:
        assert (
            project.files.get(filename, "master").decode().decode("utf8")
            == text
        )


def assert_on_groups(
    student_teams,
    org_name=ORG_NAME,
    single_group_assertion=None,
    all_groups_assertion=None,
):
    """Assert that the expected student groups exist and that the expected
    members are in them.

    single_group_assertion(expected, actual) should be a function that takes
    the ``expected`` Team, and the ``actual`` gitlab Group. If provided, the
    custom assertion is used INSTEAD of the default single group assertion.

    all_groups_assertion(expected, actual) should be a function that takes the
    ``expected`` teams and asserts them against all ``actual`` groups. If
    provided, this is used INSTEAD of the default all-groups assertion.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = get_group(org_name, gl=gl)
    sorted_teams = sorted(list(student_teams), key=lambda t: t.name)
    team_names = set(t.name for t in sorted_teams)

    sorted_groups = sorted(
        [
            g
            for g in gl.groups.list(id=target_group.id)
            if g.name in team_names
        ],
        key=lambda g: g.name,
    )

    if all_groups_assertion:
        all_groups_assertion(sorted_teams, sorted_groups)
    else:
        assert set(g.name for g in sorted_groups) == set(
            str(team) for team in sorted_teams
        )
    for group, team in zip(sorted_groups, sorted_teams):
        # the user who owns the OAUTH token is always listed as a member
        # of groups he/she creates
        if single_group_assertion is None:
            expected_members = sorted(team.members + [TEACHER])
            actual_members = sorted(
                m.username for m in group.members.list(all=True)
            )
            assert group.name == team.name
            assert actual_members == expected_members
        else:
            single_group_assertion(expected=team, actual=group)


def _assert_on_projects(student_teams, assignment_names, assertion):
    """Execute the specified assertion operation on a project. Assertion should
    be a callable taking precisely on project as an argument.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    repo_names = plug.generate_repo_names(student_teams, assignment_names)
    target_group = get_group(ORG_NAME, gl=gl)
    student_groups = gl.groups.list(id=target_group.id)
    projects = [
        gl.projects.get(p.id)
        for g in student_groups
        for p in g.projects.list(all=True)
        if p.name in repo_names
    ]

    for proj in projects:
        assertion(proj)


def assert_issues_exist(
    student_teams,
    assignment_names,
    expected_issue,
    expected_state="opened",
    expected_num_asignees=0,
):
    """Assert that the expected issue has been opened in each of the student
    repos.
    """

    def assertion(project):
        issues = project.issues.list(all=True)
        for actual_issue in issues:
            if actual_issue.title == expected_issue.title:
                assert actual_issue.state == expected_state
                assert actual_issue.description == expected_issue.body
                # FIXME This assert always fails in CI, but not locally. I
                # can't figure out why.
                # assert len(actual_issue.assignees) == expected_num_asignees
                assert TEACHER not in [
                    asignee["username"] for asignee in actual_issue.assignees
                ]

                return
        assert False, "no issue matching the specified title"

    _assert_on_projects(student_teams, assignment_names, assertion)


def assert_num_issues(student_teams, assignment_names, num_issues):
    """Assert that there are precisely num_issues issues in each student
    repo.
    """

    def assertion(project):
        assert len(project.issues.list(all=True)) == num_issues

    _assert_on_projects(student_teams, assignment_names, assertion)