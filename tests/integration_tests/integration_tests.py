import os
import shutil
import hashlib
import subprocess
import pathlib
import re
import itertools
import tempfile

import pytest
import gitlab

import repobee_plug as plug
from repobee_plug import apimeta

import _repobee.ext
import _repobee.ext.gitlab
import _repobee.cli

assert os.getenv(
    "REPOBEE_NO_VERIFY_SSL"
), "The env variable REPOBEE_NO_VERIFY_SSL must be set to 'true'"


VOLUME_DST = "/workdir"
COVERAGE_VOLUME_DST = "/coverage"
DIR = pathlib.Path(__file__).resolve().parent
TOKEN = (DIR / "token").read_text(encoding="utf-8").strip()
RESTORE_SH = DIR / "restore.sh"

OAUTH_USER = "oauth2"
BASE_DOMAIN = "gitlab.integrationtest.local"
BASE_URL = "https://" + BASE_DOMAIN
LOCAL_DOMAIN = "localhost:50443"
LOCAL_BASE_URL = "https://" + LOCAL_DOMAIN
ORG_NAME = "repobee-testing"
MASTER_ORG_NAME = "repobee-master"
ACTUAL_USER = "repobee-user"

MASTER_REPO_NAMES = "task-1 task-2 task-3".split()
STUDENT_TEAMS = [apimeta.Team(members=[s]) for s in "slarse rjglasse".split()]
STUDENT_TEAM_NAMES = [str(t) for t in STUDENT_TEAMS]
STUDENT_REPO_NAMES = plug.generate_repo_names(STUDENT_TEAMS, MASTER_REPO_NAMES)

REPOBEE_GITLAB = "repobee -p gitlab"
BASE_ARGS = ["--bu", BASE_URL, "-o", ORG_NAME, "-t", TOKEN, "--tb"]
STUDENTS_ARG = ["-s", " ".join(STUDENT_TEAM_NAMES)]
MASTER_REPOS_ARG = ["--mn", " ".join(MASTER_REPO_NAMES)]
MASTER_ORG_ARG = ["--mo", MASTER_ORG_NAME]

TASK_CONTENTS_SHAS = {
    "task-1": (
        b"\xcc\xd5\xcb\xfd\xfe\xab\xc6g\xc9{\xe4c\xd2\xc7W\xa2\\>\xac\x1a"
    ),
    "task-2": b"!o\xb02\x9b~.`\xba=\xf9d\x11\x98\xf0\xedt\x1f\xd0D",
    "task-3": b"\\\x163RV\r\xb7~n\xea\x14\xf6\xd5\xcb\xab\x82\xf9f1c",
}


def api_instance(org_name=ORG_NAME):
    """Return a valid instance of the GitLabAPI class."""
    return _repobee.ext.gitlab.GitLabAPI(LOCAL_BASE_URL, TOKEN, org_name)


def gitlab_and_groups():
    """Return a valid gitlab instance, along with the master group and the
    target group.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    master_group = gl.groups.list(search=MASTER_ORG_NAME)[0]
    target_group = gl.groups.list(search=ORG_NAME)[0]
    return gl, master_group, target_group


def assert_master_repos_exist(master_repo_names, org_name):
    """Assert that the master repos are in the specified group."""
    gl, *_ = gitlab_and_groups()
    group = gl.groups.list(search=org_name)[0]
    actual_repo_names = [g.name for g in group.projects.list()]
    assert sorted(actual_repo_names) == sorted(master_repo_names)


def assert_repos_exist(student_teams, master_repo_names, org_name=ORG_NAME):
    """Assert that the associated student repos exist."""
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    student_groups = gl.groups.list(id=target_group.id)

    projects = [p for g in student_groups for p in g.projects.list()]
    project_names = [p.name for p in projects]

    assert set(project_names) == set(repo_names)


def assert_repos_contain(
    student_teams, master_repo_names, filename, text, org=ORG_NAME
):
    """Assert that each of the student repos contain the given file."""
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    student_groups = gl.groups.list(id=target_group.id)

    projects = [
        gl.projects.get(p.id)
        for g in student_groups
        for p in g.projects.list()
        if p.name in repo_names
    ]
    assert len(projects) == len(repo_names)
    for project in projects:
        assert (
            project.files.get(filename, "master").decode().decode("utf8")
            == text
        )


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


def _assert_on_projects(student_teams, master_repo_names, assertion):
    """Execute the specified assertion operation on a project. Assertion should
    be a callable taking precisely on project as an argument.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    repo_names = plug.generate_repo_names(student_teams, master_repo_names)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    student_groups = gl.groups.list(id=target_group.id)
    projects = [
        gl.projects.get(p.id)
        for g in student_groups
        for p in g.projects.list()
        if p.name in repo_names
    ]

    for proj in projects:
        assertion(proj)


def assert_issues_exist(
    student_teams, master_repo_names, expected_issue, expected_state="opened"
):
    """Assert that the expected issue has been opened in each of the student
    repos.
    """

    def assertion(project):
        issues = project.issues.list()
        for actual_issue in issues:
            if actual_issue.title == expected_issue.title:
                assert actual_issue.state == expected_state
                return
        assert False, "no issue matching the specified title"

    _assert_on_projects(student_teams, master_repo_names, assertion)


def assert_num_issues(student_teams, master_repo_names, num_issues):
    """Assert that there are precisely num_issues issues in each student
    repo.
    """

    def assertion(project):
        assert len(project.issues.list()) == num_issues

    _assert_on_projects(student_teams, master_repo_names, assertion)


@pytest.fixture(autouse=True)
def restore():
    """Run the script that restores the GitLab instance to its initial
    state.
    """
    with open(os.devnull, "w") as devnull:
        subprocess.run(
            str(RESTORE_SH), shell=True, stdout=devnull, stderr=devnull
        )


@pytest.fixture
def tmpdir_volume_arg(tmpdir):
    """Create a temporary directory and return an argument string that
    will mount a docker volume to it.
    """
    yield "-v {}:{}".format(str(tmpdir), VOLUME_DST)


@pytest.fixture(scope="module", autouse=True)
def coverage_volume(tmp_path_factory):
    covdir = tmp_path_factory.mktemp("coverage_files")
    yield "-v {}:{}".format(str(covdir), COVERAGE_VOLUME_DST)

    covfile = covdir / ".coverage"
    assert covfile.is_file()
    cwd = pathlib.Path(".").resolve()
    shutil.copy(str(covfile), str(cwd / ".coverage"))
    shutil.move(str(covfile), str(cwd / ".coverage"))


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


def run_in_docker_with_coverage(command, extra_args=None):
    assert extra_args, "extra volume args are required to run with coverage"
    coverage_command = (
        "coverage run --branch --append --source _repobee -m " + command
    )
    return run_in_docker(coverage_command, extra_args=extra_args)


def run_in_docker(command, extra_args=None):
    extra_args = " ".join(extra_args) if extra_args else ""
    docker_command = (
        "docker run {} --net development --rm --name repobee "
        "repobee:test /bin/sh -c '{}'"
    ).format(extra_args, command)
    return subprocess.run(
        docker_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def update_repo(repo_name, filename, text):
    """Add a file with the given filename and text to the repo."""
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    proj, *_ = [
        p for p in gl.projects.list(search=repo_name) if p.name == repo_name
    ]
    env = os.environ.copy()
    env["GIT_SSL_NO_VERIFY"] = "true"
    env["GIT_AUTHOR_EMAIL"] = "slarse@kth.se"
    env["GIT_AUTHOR_NAME"] = "Simon"
    env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]
    env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
    with tempfile.TemporaryDirectory() as tmpdir:
        url_with_token = (
            proj.web_url.replace(
                "https://", "https://oauth2:{}@".format(TOKEN)
            ).replace(BASE_DOMAIN, LOCAL_DOMAIN)
            + ".git"
        )
        clone_proc = subprocess.run(
            "git clone {}".format(url_with_token).split(), cwd=tmpdir, env=env
        )
        assert clone_proc.returncode == 0

        repo_dir = pathlib.Path(tmpdir) / proj.name
        new_file = repo_dir / filename
        new_file.touch()
        new_file.write_text(text)

        add_proc = subprocess.run(
            "git add {}".format(filename).split(), cwd=str(repo_dir), env=env
        )
        assert add_proc.returncode == 0

        commit_proc = subprocess.run(
            "git commit -am newfile".split(), cwd=str(repo_dir), env=env
        )
        assert commit_proc.returncode == 0

        push_proc = subprocess.run(
            "git push".split(), cwd=str(repo_dir), env=env
        )
        assert push_proc.returncode == 0

    assert proj.files.get(filename, "master").decode().decode("utf8") == text


@pytest.fixture
def with_student_repos(restore):
    """Set up student repos before starting tests.

    Note that explicitly including restore here is necessary to ensure that
    it runs before this fixture.
    """
    command = " ".join(
        [
            REPOBEE_GITLAB,
            _repobee.cli.SETUP_PARSER,
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
    assert_groups_exist(STUDENT_TEAMS)


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


def hash_directory(path):
    shas = []
    for dirpath, _, filenames in os.walk(str(path)):
        if ".git" in dirpath:
            continue
        files = (pathlib.Path(dirpath) / filename for filename in filenames)
        shas += (hashlib.sha1(file.read_bytes()).digest() for file in files)
    return hashlib.sha1(b"".join(shas)).digest()


@pytest.fixture
def open_issues(with_student_repos):
    """Open two issues in each student repo."""
    task_issue = apimeta.Issue(
        title="Task", body="The task is to do this, this and that"
    )
    correction_issue = apimeta.Issue(
        title="Correction required", body="You need to fix this, this and that"
    )
    issues = [task_issue, correction_issue]
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    target_group = gl.groups.list(search=ORG_NAME)[0]
    projects = (
        gl.projects.get(p.id)
        for p in target_group.projects.list(include_subgroups=True)
    )
    for project in projects:
        project.issues.create(
            dict(title=task_issue.title, body=task_issue.body)
        )
        project.issues.create(
            dict(title=correction_issue.title, body=correction_issue.body)
        )

    assert_num_issues(STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, len(issues))
    assert_issues_exist(STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, task_issue)
    assert_issues_exist(
        STUDENT_TEAM_NAMES, MASTER_REPO_NAMES, correction_issue
    )

    return issues


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestClone:
    """Integration tests for the clone command."""

    def test_clean_clone(self, with_student_repos, tmpdir, extra_args):
        """Test cloning student repos when there are no repos in the current
        working directory.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

    def test_clone_twice(self, with_student_repos, tmpdir, extra_args):
        """Cloning twice in a row should have the same effect as cloning once.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        first_result = run_in_docker_with_coverage(
            command, extra_args=extra_args
        )
        second_result = run_in_docker_with_coverage(
            command, extra_args=extra_args
        )

        assert first_result.returncode == 0
        assert second_result.returncode == 0
        assert_cloned_repos(STUDENT_REPO_NAMES, tmpdir)

    def test_clone_does_not_create_dirs_on_fail(
        self, with_student_repos, tmpdir, extra_args
    ):
        """Test that no local directories are created for repos that RepoBee
        fails to pull.
        """
        non_existing_master_repo_names = ["non-existing-1", "non-existing-2"]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.CLONE_PARSER,
                *BASE_ARGS,
                *STUDENTS_ARG,
                "--mn",
                " ".join(non_existing_master_repo_names),
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert [
            dir for dir in os.listdir(str(tmpdir)) if os.path.isdir(dir)
        ] == []

    def test_clone_does_not_alter_existing_dirs(
        self, with_student_repos, tmpdir, extra_args
    ):
        """Test that clone does not clobber existing directories."""
        team_with_local_repos = STUDENT_TEAMS[0]
        teams_without_local_repos = STUDENT_TEAMS[1:]
        pre_existing_dirnames = plug.generate_repo_names(
            [team_with_local_repos], MASTER_REPO_NAMES
        )
        non_pre_existing_dirnames = plug.generate_repo_names(
            teams_without_local_repos, MASTER_REPO_NAMES
        )

        expected_dir_hashes = dict()
        for dirname in pre_existing_dirnames:
            new_dir = tmpdir.mkdir(dirname)
            new_file = new_dir.join("file")
            new_file.write_text(dirname, encoding="utf-8")
            expected_dir_hashes[dirname] = hash_directory(new_dir)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.CLONE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_cloned_repos(non_pre_existing_dirnames, tmpdir)
        for dirname in pre_existing_dirnames:
            dirhash = hash_directory(pathlib.Path(str(tmpdir)) / dirname)
            assert dirhash == expected_dir_hashes[dirname]


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestSetup:
    """Integration tests for the setup command."""

    def test_clean_setup(self, extra_args):
        """Test a first-time setup with master repos in the master org."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.SETUP_PARSER,
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_groups_exist(STUDENT_TEAMS)

    def test_setup_twice(self, extra_args):
        """Setting up twice should have the same effect as setting up once."""
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.SETUP_PARSER,
                *BASE_ARGS,
                *MASTER_ORG_ARG,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_exist(STUDENT_TEAMS, MASTER_REPO_NAMES)
        assert_groups_exist(STUDENT_TEAMS)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestUpdate:
    """Integration tests for the update command."""

    def test_happy_path(self, with_student_repos, extra_args):
        master_repo = MASTER_REPO_NAMES[0]
        filename = "superfile.super"
        text = "some epic content\nfor this file!"
        update_repo(master_repo, filename, text)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.UPDATE_PARSER,
                *MASTER_ORG_ARG,
                *BASE_ARGS,
                "--mn",
                master_repo,
                *STUDENTS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        assert result.returncode == 0
        assert_repos_contain(STUDENT_TEAMS, [master_repo], filename, text)

    def test_opens_issue_if_update_rejected(
        self, tmpdir, with_student_repos, extra_args
    ):
        master_repo = MASTER_REPO_NAMES[0]
        conflict_repo = plug.generate_repo_name(STUDENT_TEAMS[0], master_repo)
        filename = "superfile.super"
        text = "some epic content\nfor this file!"
        # update the master repo
        update_repo(master_repo, filename, text)
        # conflicting update in the student repo
        update_repo(conflict_repo, "somefile.txt", "some other content")

        issue = plug.Issue(title="Oops, push was rejected!", body="")
        issue_file = pathlib.Path(str(tmpdir)) / "issue.md"
        issue_file.write_text(issue.title)

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.UPDATE_PARSER,
                *MASTER_ORG_ARG,
                *BASE_ARGS,
                "--mn",
                master_repo,
                *STUDENTS_ARG,
                "--issue",
                issue_file.name,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_repos_contain(STUDENT_TEAMS[1:], [master_repo], filename, text)
        assert_issues_exist(STUDENT_TEAMS[0:1], [master_repo], issue)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestMigrate:
    """Integration tests for the migrate command."""

    @pytest.fixture
    def local_master_repos(self, restore, extra_args):
        """Clone the master repos to disk. The restore fixture is explicitly
        included as it must be run before this fixture.
        """
        api = api_instance(MASTER_ORG_NAME)
        master_repo_urls = [
            url.replace(LOCAL_DOMAIN, BASE_DOMAIN)
            for url in api.get_repo_urls(MASTER_REPO_NAMES)
        ]
        # clone the master repos to disk first first
        git_commands = ["git clone {}".format(url) for url in master_repo_urls]
        result = run_in_docker(
            " && ".join(git_commands), extra_args=extra_args
        )

        assert result.returncode == 0
        return MASTER_REPO_NAMES

    def test_happy_path(self, local_master_repos, extra_args):
        """Migrate a few repos from the existing master repo into the target
        organization.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.MIGRATE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_master_repos_exist(local_master_repos, ORG_NAME)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestOpenIssues:
    """Tests for the open-issues command."""

    _ISSUE = apimeta.Issue(title="This is a title", body="This is a body")

    def test_happy_path(self, tmpdir_volume_arg, tmpdir, extra_args):
        """Test opening an issue in each student repo."""
        filename = "issue.md"
        text = "{}\n{}".format(self._ISSUE.title, self._ISSUE.body)
        tmpdir.join(filename).write_text(text, encoding="utf-8")

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.OPEN_ISSUE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-i",
                "{}/{}".format(VOLUME_DST, filename),
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_num_issues(STUDENT_TEAMS, MASTER_REPO_NAMES, 1)
        assert_issues_exist(STUDENT_TEAMS, MASTER_REPO_NAMES, self._ISSUE)


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestCloseIssues:
    """Tests for the close-issues command."""

    def test_closes_only_matched_issues(self, open_issues, extra_args):
        """Test that close-issues respects the regex."""
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        close_issue = open_issues[0]
        open_issue = open_issues[1]
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.CLOSE_ISSUE_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-r",
                close_issue.title,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        assert_issues_exist(
            STUDENT_TEAM_NAMES,
            MASTER_REPO_NAMES,
            close_issue,
            expected_state="closed",
        )
        assert_issues_exist(
            STUDENT_TEAM_NAMES,
            MASTER_REPO_NAMES,
            open_issue,
            expected_state="opened",
        )


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestListIssues:
    """Tests for the list-issues command."""

    def test_lists_matching_issues(self, open_issues, extra_args):
        assert len(open_issues) == 2, "expected there to be only 2 open issues"
        matched = open_issues[0]
        unmatched = open_issues[1]
        repo_names = plug.generate_repo_names(STUDENT_TEAMS, MASTER_REPO_NAMES)

        issue_pattern_template = r"^\[INFO\].*{}/#\d:\s+{}.*by {}.?$"
        expected_issue_output_patterns = [
            issue_pattern_template.format(
                repo_name, matched.title, ACTUAL_USER
            )
            for repo_name in repo_names
        ]
        unexpected_issue_output_patterns = [
            issue_pattern_template.format(
                repo_name, unmatched.title, ACTUAL_USER
            )
            for repo_name in repo_names
        ]

        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.LIST_ISSUES_PARSER,
                *BASE_ARGS,
                *MASTER_REPOS_ARG,
                *STUDENTS_ARG,
                "-r",
                matched.title,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)
        output = result.stdout.decode("utf-8")

        assert result.returncode == 0
        search_flags = re.MULTILINE
        for expected_pattern in expected_issue_output_patterns:
            assert re.search(expected_pattern, output, search_flags)
        for unexpected_pattern in unexpected_issue_output_patterns:
            assert not re.search(unexpected_pattern, output, search_flags)
