import os
import pathlib
from functools import partial
from unittest import mock
from unittest.mock import patch, MagicMock, call, PropertyMock

import pytest

import _repobee
import _repobee.ext.github
from _repobee import command
from _repobee import git
from _repobee import util
from _repobee import exception
from _repobee import plugin

import repobee_plug as plug

import constants
import functions

from_magic_mock_issue = functions.from_magic_mock_issue
to_magic_mock_issue = functions.to_magic_mock_issue
TOKEN = constants.TOKEN

random_date = functions.random_date

OPEN_ISSUES = [
    plug.Issue(
        "close this issue", "This is a body", 3, random_date(), "slarse"
    ),
    plug.Issue(
        "Don't close this issue", "Another body", 4, random_date(), "glassey"
    ),
]

CLOSED_ISSUES = [
    plug.Issue(
        "This is a closed issue",
        "With an uninteresting body that has a single very,"
        "very long line that would probably break the implementation "
        "if something was off with the line limit function.",
        1,
        random_date(),
        "tmore",
    ),
    plug.Issue(
        "Yet another closed issue",
        "Even less interesting body",
        2,
        random_date(),
        "viklu",
    ),
]

ORG_NAME = "test-org"
BASE_URL = "https://some_enterprise_host/api/v3"
ISSUE = plug.Issue(
    "Oops, something went wrong!", "This is the body **with some formatting**."
)
PLUGINS = (constants.PLUGINS,)
STUDENTS = constants.STUDENTS


def repo_generator(teams, master_repo_names):
    for repo_name in plug.generate_repo_names(teams, master_repo_names):
        yield plug.Repo(
            name=repo_name,
            url=generate_repo_url(repo_name),
            private=True,
            description="",
        )


def generate_team_repo_url(student, base_name):
    return "https://slarse.se/repos/{}".format(
        plug.generate_repo_name(student, base_name)
    )


def generate_repo_url(name):
    return generate_team_repo_url(name, "d")[:-2]


def get_repo_urls_fake(self, master_repo_names, org_name=None, teams=None):
    return list(
        map(
            generate_repo_url,
            master_repo_names
            if not teams
            else plug.generate_repo_names(teams, master_repo_names),
        )
    )


# TODO remove dependency on _apimeta, it is private behavior!
plug._apimeta.check_parameters(plug.API.get_repo_urls, get_repo_urls_fake)

MASTER_NAMES = ("week-1", "week-2", "week-3")
MASTER_URLS = tuple(generate_repo_url(name) for name in MASTER_NAMES)

STUDENT_REPO_NAMES = tuple(
    plug.generate_repo_name(student, master_name)
    for master_name in MASTER_NAMES
    for student in STUDENTS
)

raise_ = functions.raise_


@pytest.fixture(autouse=True)
def git_mock(request, mocker):
    """Mocks the whole git module so that there are no accidental
    pushes/clones.
    """
    if "nogitmock" in request.keywords:
        return
    pt = _repobee.git.Push
    git_mock = mocker.patch("_repobee.command.repos.git", autospec=True)
    git_mock.Push = pt
    return git_mock


def _get_issues(repo_names, state=plug.IssueState.OPEN, title_regex=""):
    """Bogus version of GitHubAPI.get_issues"""
    for repo_name in repo_names:
        if repo_name == STUDENT_REPO_NAMES[-2]:
            # repo without issues
            yield repo_name, iter([])
        elif repo_name in STUDENT_REPO_NAMES:
            if state == plug.IssueState.OPEN:
                issues = iter(OPEN_ISSUES)
            elif state == plug.IssueState.CLOSED:
                issues = iter(CLOSED_ISSUES)
            elif state == plug.IssueState.ALL:
                issues = iter(OPEN_ISSUES + CLOSED_ISSUES)
            else:
                raise ValueError("Unexpected value for 'state': ", state)
            yield repo_name, issues


@pytest.fixture(autouse=True)
def api_mock(request, mocker):
    if "noapimock" in request.keywords:
        return

    def url_from_repo_info(repo_info):
        return generate_repo_url(repo_info.name)

    mock = MagicMock(spec=_repobee.ext.github.GitHubAPI)
    api_class = mocker.patch("_repobee.ext.github.GitHubAPI", autospec=True)
    api_class.return_value = mock

    mock.get_repo_urls.side_effect = partial(
        get_repo_urls_fake, None  # pass None for self arg
    )
    mock.create_repos.side_effect = lambda repo_infos: list(
        map(url_from_repo_info, repo_infos)
    )
    mock.get_issues = MagicMock(
        spec="_repobee.ext.github.GitHubAPI.get_issues",
        side_effect=_get_issues,
    )
    type(mock).token = PropertyMock(return_value=TOKEN)
    return mock


@pytest.fixture
def students():
    return list(STUDENTS)


@pytest.fixture
def ensure_teams_and_members_mock(api_mock, students):
    api_mock.ensure_teams_and_members.side_effect = lambda teams: [
        plug.Team(name=str(student), members=[student], id=id)
        for id, student in enumerate(students)
    ]


@pytest.fixture
def master_urls():
    return list(MASTER_URLS)


@pytest.fixture
def master_names():
    return list(MASTER_NAMES)


@pytest.fixture
def repo_infos(master_urls, students):
    """Students are here used as teams, remember that they have same names as
    students.
    """
    repo_infos = []
    for url in master_urls:
        repo_base_name = util.repo_name(url)
        repo_infos += [
            plug.Repo(
                name=plug.generate_repo_name(student, repo_base_name),
                description="{} created for {}".format(
                    repo_base_name, student
                ),
                private=True,
                team_id=cur_id,
            )
            for cur_id, student in enumerate(students)
        ]
    return repo_infos


@pytest.fixture
def push_tuples(master_urls, students, tmpdir):

    push_tuples = [
        git.Push(
            local_path=os.path.join(str(tmpdir), util.repo_name(url)),
            repo_url=generate_team_repo_url(student, util.repo_name(url)),
            branch="master",
        )
        # note that the order here is significant, must correspond with
        # plug.generate_repo_names
        for url in master_urls
        for student in students
    ]
    return push_tuples


@pytest.fixture(scope="function", autouse=True)
def rmtree_mock(mocker):
    return mocker.patch("shutil.rmtree", autospec=True)


@pytest.fixture(autouse=True)
def is_git_repo_mock(mocker):
    return mocker.patch(
        "_repobee.util.is_git_repo", return_value=True, autospec=True
    )


@pytest.fixture(autouse=True)
def tmpdir_mock(mocker, tmpdir):
    mock = mocker.patch("tempfile.TemporaryDirectory", autospec=True)
    mock.return_value.__enter__.return_value = str(tmpdir)
    return mock


def assert_raises_on_duplicate_master_urls(function, master_urls, students):
    """Test for functions that take master_urls and students args."""

    master_urls.append(master_urls[0])

    with pytest.raises(ValueError) as exc_info:
        function(master_urls, students, ORG_NAME, BASE_URL)
    assert str(exc_info.value) == "master_repo_urls contains duplicates"


class TestSetupStudentRepos:
    """Tests for setup_student_repos."""

    @pytest.fixture(autouse=True)
    def is_git_repo_mock(self, mocker):
        return mocker.patch("_repobee.util.is_git_repo", return_value=True)

    def test_raises_on_clone_failure(
        self, master_urls, students, git_mock, api_mock
    ):
        git_mock.clone_single.side_effect = lambda url, cwd: raise_(
            exception.CloneFailedError("clone failed", 128, b"some error", url)
        )()

        with pytest.raises(exception.CloneFailedError) as exc_info:
            command.setup_student_repos(master_urls, students, api_mock)

        assert exc_info.value.url == master_urls[0]

    def test_raises_on_duplicate_master_urls(
        self, mocker, master_urls, students, api_mock
    ):
        master_urls.append(master_urls[0])

        with pytest.raises(ValueError) as exc_info:
            command.setup_student_repos(master_urls, students, api_mock)
        assert str(exc_info.value) == "master_repo_urls contains duplicates"

    def test_happy_path(
        self,
        mocker,
        master_urls,
        students,
        api_mock,
        git_mock,
        repo_infos,
        push_tuples,
        ensure_teams_and_members_mock,
        tmpdir,
    ):
        """Test that setup_student_repos makes the correct function calls."""
        expected_clone_calls = [
            call(url, cwd=str(tmpdir)) for url in master_urls
        ]

        command.setup_student_repos(master_urls, students, api_mock)

        git_mock.clone_single.assert_has_calls(expected_clone_calls)
        api_mock.ensure_teams_and_members.assert_called_once_with(students)
        api_mock.create_repos.assert_called_once_with(repo_infos)
        git_mock.push.assert_called_once_with(push_tuples)


class TestUpdateStudentRepos:
    """Tests for update_student_repos."""

    @staticmethod
    def generate_url(repo_name):
        return "{}/{}/{}".format(BASE_URL, ORG_NAME, repo_name)

    def test_raises_on_duplicate_master_urls(
        self, mocker, master_urls, students, api_mock
    ):
        master_urls.append(master_urls[0])

        with pytest.raises(ValueError) as exc_info:
            command.update_student_repos(master_urls, students, api_mock)
        assert str(exc_info.value) == "master_repo_urls contains duplicates"

    def test_happy_path(
        self,
        git_mock,
        master_urls,
        students,
        api_mock,
        push_tuples,
        rmtree_mock,
        tmpdir,
    ):
        """Test that update_student_repos makes the correct function calls.

        NOTE: Ignores the git mock.
        """
        expected_clone_calls = [
            call(url, cwd=str(tmpdir)) for url in master_urls
        ]

        command.update_student_repos(master_urls, students, api_mock)

        git_mock.clone_single.assert_has_calls(expected_clone_calls)
        git_mock.push.assert_called_once_with(push_tuples)

    @pytest.mark.nogitmock
    @pytest.mark.parametrize(
        "issue",
        [plug.Issue("Oops", "Sorry, we failed to push to your repo!"), None],
    )
    def test_issues_on_exceptions(
        self, issue, mocker, api_mock, repo_infos, push_tuples, rmtree_mock
    ):
        """Test that issues are opened in repos where pushing fails, if and
        only if the issue is not None.

        IMPORTANT NOTE: the git_mock fixture is ignored in this test. Be
        careful.
        """
        students = list("abc")
        master_name = "week-1"
        master_urls = [
            "https://some-host/repos/{}".format(name)
            for name in [master_name, "week-3"]
        ]

        fail_students = ["a", "c"]
        fail_repo_names = plug.generate_repo_names(
            fail_students, [master_name]
        )
        fail_repo_urls = get_repo_urls_fake(
            # passing None for self is fine here
            None,
            [master_name],
            teams=fail_students,
        )

        async def raise_specific(pt):
            if pt.repo_url in fail_repo_urls:
                raise exception.PushFailedError(
                    "Push failed", 128, b"some error", pt.repo_url
                )

        mocker.patch("_repobee.git._push_async", side_effect=raise_specific)
        mocker.patch("_repobee.git.clone_single")

        command.update_student_repos(master_urls, students, api_mock, issue)

        if issue:  # expect issue to be opened
            call_list = api_mock.open_issue.call_args_list
            call = call_list[0]
            args = call[0]
            assert len(call_list) == 1
            assert args[0] == issue.title
            assert args[1] == issue.body
            assert sorted(args[2]) == sorted(fail_repo_names)
        else:  # expect issue not to be opened
            assert not api_mock.open_issue.called

    @pytest.mark.nogitmock
    def test_issues_arent_opened_on_exceptions_if_unspeficied(
        self, mocker, api_mock, repo_infos, push_tuples, rmtree_mock
    ):
        """Test that issues are not opened in repos where pushing fails, no
        issue has been given.

        IMPORTANT NOTE: the git_mock fixture is ignored in this test. Be
        careful.
        """
        students = list("abc")
        master_name = "week-1"
        master_urls = [
            "https://some-host/repos/{}".format(name)
            for name in [master_name, "week-3"]
        ]

        fail_repo_names = [
            plug.generate_repo_name(stud, master_name) for stud in ["a", "c"]
        ]
        fail_repo_urls = [self.generate_url(name) for name in fail_repo_names]

        async def raise_specific(pt):
            if pt.repo_url in fail_repo_urls:
                raise exception.PushFailedError(
                    "Push failed", 128, b"some error", pt.repo_url
                )

        mocker.patch("_repobee.git._push_async", side_effect=raise_specific)
        mocker.patch("_repobee.git.clone_single")

        command.update_student_repos(master_urls, students, api_mock)

        assert not api_mock.open_issue.called


class TestOpenIssue:
    """Tests for open_issue."""

    def test_happy_path(self, mocker, api_mock):
        master_names = ["week-1", "week-2"]
        students = list("abc")
        expected_repo_names = [
            "a-week-1",
            "b-week-1",
            "c-week-1",
            "a-week-2",
            "b-week-2",
            "c-week-2",
        ]

        issue = plug.Issue(
            "A title", "And a nice **formatted** body\n### With headings!"
        )
        command.open_issue(issue, master_names, students, api_mock)

        api_mock.open_issue.assert_called_once_with(
            issue.title, issue.body, expected_repo_names
        )


class TestCloseIssue:
    """Tests for close_issue."""

    def test_happy_path(self, api_mock):
        title_regex = r"some-regex\d\w"
        master_names = ["week-1", "week-2"]
        students = list("abc")
        repos = repo_generator(students, master_names)
        expected_repos = list(repos)

        command.close_issue(title_regex, repos, api_mock)

        calls = api_mock.close_issue.mock_calls
        assert len(calls) == 1
        actual_regex, actual_repos = calls[0].args
        assert actual_regex == title_regex
        assert sorted(actual_repos) == sorted(expected_repos)


class TestCloneRepos:
    """Tests for clone_repos."""

    @pytest.fixture
    def register_default_plugins(self):
        plugin_names = plugin.resolve_plugin_names(
            plugin_names=constants.PLUGINS
        )
        modules = plugin.load_plugin_modules(plugin_names)
        plugin.register_plugins(modules)

    @pytest.fixture
    def act_mocks(self, monkeypatch, config_mock):
        """Mocks for the act functions and method. This is a bit
        messy as the functions must be marked with the
        repobee_plug.repobee_hook decorator to be picked up by pluggy.
        """
        javac_hook = MagicMock(
            spec="_repobee.ext.javac.JavacCloneHook._class._act",
            return_value=plug.Result(
                "javac", plug.Status.SUCCESS, "Great success!"
            ),
        )
        pylint_hook = MagicMock(
            spec="_repobee.ext.pylint.act",
            return_value=plug.Result(
                "pylint", plug.Status.WARNING, "Minor warning."
            ),
        )

        @plug.repobee_hook
        def act_hook_func(path, api):
            return pylint_hook(path)

        @plug.repobee_hook
        def act_hook_meth(self, path, api):
            return javac_hook(self, path)

        monkeypatch.setattr(
            "_repobee.ext.javac.JavacCloneHook._act", act_hook_meth
        )
        monkeypatch.setattr("_repobee.ext.pylint.act", act_hook_func)
        _repobee.ext.pylint.act(None, None)

        plugin_names = plugin.resolve_plugin_names(
            plugin_names=constants.PLUGINS
        )
        modules = plugin.load_plugin_modules(plugin_names)
        plugin.register_plugins(modules)

        return javac_hook, pylint_hook

    @pytest.fixture
    def get_plugin_names_mock(self, mocker):
        return mocker.patch(
            "_repobee.config.get_plugin_names", return_value=PLUGINS
        )

    def test_happy_path(
        self, api_mock, git_mock, master_names, students, tmpdir
    ):
        """Tests that the correct calls are made when there are no errors."""
        command.clone_repos(repo_generator(students, master_names), api_mock)

        # note that the tmpdir_mock fixture sets the return value of
        # tmpdir.TemporaryDirectory to tmpdir!
        # TODO: improve assert, but as its a generator it's tricky
        git_mock.clone.assert_called_once_with(mock.ANY, cwd=str(tmpdir))

    def test_executes_act_hooks(
        self, api_mock, git_mock, master_names, students, act_mocks
    ):
        javac_hook, pylint_hook = act_mocks
        repo_names = plug.generate_repo_names(students, master_names)
        repos = repo_generator(students, master_names)

        with patch(
            "pathlib.Path.glob",
            side_effect=lambda _: (pathlib.Path(name) for name in repo_names),
        ), patch("shutil.copytree"):
            hook_results = command.clone_repos(repos, api_mock)

        assert len(hook_results) == len(repo_names)
        for repo_name in repo_names:
            assert repo_name in hook_results
            results = sorted(hook_results[repo_name])
            assert len(results) == 2
            assert results[0].name == "javac"
            assert results[1].name == "pylint"

    def test_executes_clone_tasks(
        self, master_names, students, api_mock, git_mock
    ):
        plug_name = "postflight"
        modules = plugin.load_plugin_modules([plug_name])
        plugin.register_plugins(modules)
        repo_names = plug.generate_repo_names(students, master_names)
        repos = repo_generator(students, master_names)

        for p in plug.manager.get_plugins():
            with patch(
                "pathlib.Path.glob",
                side_effect=lambda _: (
                    pathlib.Path(name) for name in repo_names
                ),
            ), patch("shutil.copytree"):
                hook_results = command.clone_repos(repos, api_mock)

        assert len(hook_results) == len(repo_names)
        for repo_name in repo_names:
            assert repo_name in hook_results
            results = hook_results[repo_name]
            assert len(results) == 1
            res = results[0]
            assert res.status == plug.Status.SUCCESS
            assert res.name == plug_name


class TestMigrateRepo:
    """Tests for migrate_repo."""

    @pytest.mark.nogitmock
    def test_happy_path(
        self, mocker, api_mock, ensure_teams_and_members_mock, tmpdir
    ):
        """Test that the correct calls are made to the api and git.

        IMPORTANT: Note that this test ignores the git mock. Be careful.
        """
        master_urls = [
            "https://some-url-to-/master/repos/week-1",
            "https://some-url-to-/master/repos/week-5",
        ]
        master_names = [util.repo_name(url) for url in master_urls]
        expected_push_urls = [generate_repo_url(name) for name in master_names]
        expected_pts = [
            git.Push(
                local_path=os.path.join(str(tmpdir), name),
                repo_url=url,
                branch="master",
            )
            for name, url in zip(master_names, expected_push_urls)
        ]
        expected_clone_calls = [
            call(url, cwd=str(tmpdir)) for url in master_urls
        ]

        api_mock.create_repos.side_effect = lambda infos: [
            generate_repo_url(info.name) for info in infos
        ]
        git_clone_mock = mocker.patch(
            "_repobee.git.clone_single", autospec=True
        )
        git_push_mock = mocker.patch("_repobee.git.push", autospec=True)

        command.migrate_repos(master_urls, api_mock)

        git_clone_mock.assert_has_calls(expected_clone_calls)
        assert api_mock.create_repos.called
        assert (
            not api_mock.ensure_teams_and_members.called
        ), "master repos should no longer be added to a team"
        git_push_mock.assert_called_once_with(expected_pts)


class TestListIssues:
    """Tests for list_issues. Since this is essentially just a print command,
    it is only tested for stability.
    """

    @pytest.mark.parametrize(
        "state",
        (plug.IssueState.OPEN, plug.IssueState.CLOSED, plug.IssueState.ALL),
    )
    @pytest.mark.parametrize("regex", ("", r"^.*$"))
    @pytest.mark.parametrize("show_body", (True, False))
    @pytest.mark.parametrize("author", (None, "slarse"))
    def test_happy_path(
        self, master_names, students, api_mock, state, regex, show_body, author
    ):
        repos = repo_generator(students, master_names)

        command.list_issues(
            repos,
            api_mock,
            state=state,
            title_regex=regex,
            show_body=show_body,
            author=author,
        )

        api_mock.get_issues.assert_called_once_with(
            list(STUDENT_REPO_NAMES), state, regex
        )


# TODO add more test cases
def test_purge_review_teams(master_names, students, api_mock):
    expected_review_teams = [
        plug.generate_review_team_name(s, mn)
        for s in students
        for mn in master_names
    ]

    command.purge_review_teams(master_names, students, api_mock)

    api_mock.delete_teams.assert_called_once_with(expected_review_teams)


# TODO add more test cases
class TestAssignPeerReviewers:
    @pytest.fixture(autouse=True)
    def load_default_plugins(self):
        modules = plugin.load_plugin_modules(
            [_repobee.constants.DEFAULT_PLUGIN]
        )
        plugin.register_plugins(modules)

    @pytest.mark.parametrize(
        "num_students, num_reviews",
        [(3, 3), (3, 4)],  # equal amount  # more reviews than students
    )
    def test_too_few_students_raises(
        self, master_names, students, api_mock, num_students, num_reviews
    ):
        teams = students[:num_students]

        with pytest.raises(ValueError) as exc_info:
            command.assign_peer_reviews(
                master_repo_names=master_names,
                teams=teams,
                num_reviews=num_reviews,
                issue=None,
                api=api_mock,
            )

        assert "num_reviews must be less than" in str(exc_info.value)

    def test_zero_reviews_raises(self, master_names, students, api_mock):
        num_reviews = 0

        with pytest.raises(ValueError) as exc_info:
            command.assign_peer_reviews(
                master_repo_names=master_names,
                teams=students,
                num_reviews=num_reviews,
                issue=None,
                api=api_mock,
            )

        assert "num_reviews must be greater than 0" in str(exc_info.value)

    def test_happy_path(self, master_names, students, api_mock):
        issue = plug.Issue("this is a title", "this is a body")
        mappings = [
            {
                plug.generate_review_team_name(student, master_name): [
                    plug.generate_repo_name(student, master_name)
                ]
                for student in students
            }
            for master_name in master_names
        ]

        expected_calls = [call(mapping, issue=issue) for mapping in mappings]
        num_reviews = 3

        command.assign_peer_reviews(
            master_repo_names=master_names,
            teams=students,
            num_reviews=num_reviews,
            issue=issue,
            api=api_mock,
        )

        assert api_mock.ensure_teams_and_members.called
        api_mock.add_repos_to_review_teams.assert_has_calls(
            expected_calls, any_order=True
        )


class TestCheckPeerReviewProgress:
    """Tests for check_peer_review_progress"""

    def test_happy_path(self, master_names, students, api_mock):
        """Pretty much just tests that there is no crash when calling the
        method with reasonable args.
        """
        title_regex = "Peer"
        review_team_names = [
            plug.generate_review_team_name(student, master_name)
            for student in students
            for master_name in master_names
        ]

        command.check_peer_review_progress(
            master_names, students, title_regex, 2, api_mock
        )

        api_mock.get_review_progress.assert_called_once_with(
            review_team_names, students, title_regex
        )


class TestSetupTask:
    """Tests for the setup and update commands when it comes to the setup_task
    hook.
    """

    @pytest.mark.parametrize(
        "cmd", [command.setup_student_repos, command.update_student_repos]
    )
    def test_executes_setup_hooks(self, master_urls, students, api_mock, cmd):
        """Test that the setup hooks are executed."""
        plug_name = "preflight"
        modules = plugin.load_plugin_modules([plug_name])
        plugin.register_plugins(modules)

        with patch(
            "pathlib.Path.glob",
            return_value=(pathlib.Path(name) for name in MASTER_NAMES),
        ), patch("shutil.copytree"):
            hook_results = cmd(master_urls, students, api_mock)

        assert len(hook_results) == len(
            master_urls
        ), "expected as many hook results as master repos"
        for master_repo_name in MASTER_NAMES:
            assert (
                master_repo_name in hook_results
            ), "expected hook result for master repo {}".format(
                master_repo_name
            )
            results = hook_results[master_repo_name]
            assert len(results) == 1, "expected only a single hook result"
            res = results[0]
            assert res.status == plug.Status.SUCCESS
