import itertools
from helpers import *


def assert_master_repos_exist(master_repo_names, org_name):
    """Assert that the master repos are in the specified group."""
    gl, *_ = gitlab_and_groups()
    group = gl.groups.list(search=org_name)[0]
    actual_repo_names = [g.name for g in group.projects.list(all=True)]
    assert sorted(actual_repo_names) == sorted(master_repo_names)


def assert_repos_exist(student_teams, master_repo_names, org_name):
    """Assert that the associated student repos exist."""
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=org_name)[0]
    student_groups = gl.groups.list(id=target_group.id)

    projects = [p for g in student_groups for p in g.projects.list(all=True)]
    project_names = [p.name for p in projects]

    assert set(project_names) == set(repo_names)


def assert_repos_contain(
    student_teams, master_repo_names, filename, text, org_name
):
    """Assert that each of the student repos contain the given file."""
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=org_name)[0]
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
    org_name,
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
    target_group = gl.groups.list(search=org_name)[0]
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
            expected_members = sorted(team.members + [ACTUAL_USER])
            actual_members = sorted(
                m.username for m in group.members.list(all=True)
            )
            assert group.name == team.name
            assert actual_members == expected_members
        else:
            single_group_assertion(expected=team, actual=group)


def _assert_on_projects(student_teams, master_repo_names, assertion, org_name):
    """Execute the specified assertion operation on a project. Assertion should
    be a callable taking precisely on project as an argument.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    target_group = gl.groups.list(search=org_name)[0]
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
    org_name,
    student_teams,
    master_repo_names,
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
                assert len(actual_issue.assignees) == expected_num_asignees
                assert ACTUAL_USER not in [
                    asignee["username"] for asignee in actual_issue.assignees
                ]

                return
        assert False, "no issue matching the specified title"

    _assert_on_projects(student_teams, master_repo_names, assertion, org_name)


def assert_num_issues(org_name, student_teams, master_repo_names, num_issues):
    """Assert that there are precisely num_issues issues in each student
    repo.
    """

    def assertion(project):
        assert len(project.issues.list(all=True)) == num_issues

    _assert_on_projects(student_teams, master_repo_names, assertion, org_name)


def assert_cloned_repos(repo_names, tmpdir):
    """Check that the cloned repos have the expected contents.

    NOTE: Only checks the contents of the root of the project.
    """
    # group by master repo name, all of which have the same length
    grouped_repo_names = itertools.groupby(
        sorted(repo_names),
        key=lambda name: name[len(name) - len(MASTER_REPO_NAMES[0]) :],
    )

    root = pathlib.Path(tmpdir).resolve()

    for master_repo_name, student_repo_names in grouped_repo_names:

        expected_sha = TASK_CONTENTS_SHAS[master_repo_name]
        for repo_name in student_repo_names:
            sha = hash_directory(root / repo_name)
            assert sha == expected_sha
            assert (root / repo_name / ".git").is_dir()
