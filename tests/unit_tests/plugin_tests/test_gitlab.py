from collections import namedtuple

import requests.exceptions
import pytest
import gitlab
import repobee_plug as plug

import _repobee
from _repobee import exception

import constants


class Group:
    """Class mimicking a gitlab.Group"""

    _Members = namedtuple("_Members", ("create", "list"))
    _Member = namedtuple("_Member", ("id", "access_level", "username"))

    def __init__(self, id, name, path, parent_id, users_read_only):
        self.id = id
        self.name = name
        self.path = path
        self.parent_id = parent_id
        self.members = self._Members(
            create=self._create_member, list=self._list_members
        )
        self._member_list = []
        self._users_read_only = users_read_only or {}
        # the group owner is always added to the group with max access level
        owner_id = [
            uid
            for uid, user in self._users_read_only.items()
            if user.username == constants.USER
        ][0]
        owner_data = {"user_id": owner_id, "access_level": gitlab.OWNER_ACCESS}
        self._create_member(owner_data)
        self._deleted = False

    def _create_member(self, data):
        user_id = data["user_id"]
        access_level = data["access_level"]
        if user_id in [m.id for m in self._list_members()]:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=409, error_message="Member already exists"
            )
        self._member_list.append(
            self._Member(
                id=user_id,
                access_level=access_level,
                username=self._users_read_only[user_id].username,
            )
        )

    def _list_members(self):
        return list(self._member_list)

    def delete(self):
        self._deleted = True

    @property
    def tests_only_deleted(self):
        return self._deleted


class Project:
    """Class mimicking a gitlab.Project"""

    def __init__(
        self, id, name, path, description, visibility, namespace_id, http_url
    ):
        """The http_url argument does not exist in the real gitlab api, it's
        only for testing.
        """
        self.id = id
        self.name = name
        self.path = path
        self.description = description
        self.visibility = visibility
        self.namespace_id = namespace_id
        self.attributes = dict(http_url_to_repo=http_url)


User = namedtuple("User", ("id", "username"))


class GitLabMock:
    """Class representing a GitLab instance, with the subset of functionality
    required for RepoBee to work. It may seem counterintuitive to create this
    much logic to test a class, but from experience it became much more
    complicated to try to mock out individual pieces, when those individual
    pieces exhibit interconnected behavior.

    The _groups and _users dictionaries are indexed by id, while the _projects
    dictionary is indexed by the full path to it.
    """

    _Groups = namedtuple("_Groups", ("create", "list", "get"))
    _Users = namedtuple("_Users", ("list"))
    _Projects = namedtuple("_Projects", "create get".split())

    def __init__(self, url, private_token, ssl_verify):
        self._users = {
            id: User(id=id, username=str(grp))
            for id, grp in enumerate(constants.STUDENTS + (constants.USER,))
        }
        self._owner, *_ = [
            usr
            for usr in self._users.values()
            if usr.username == constants.USER
        ]
        self._base_url = url
        self._private_token = private_token
        self._groups = {}
        self._projects = {}
        self._id = len(self._users)
        self._create_group({"name": TARGET_GROUP, "path": TARGET_GROUP})

        # this is only for testing purposes, does not exist in the real class
        self._target_group_id = list(self._groups.keys())[0]

    def auth(self):
        if self._base_url != BASE_URL:
            raise requests.exceptions.ConnectionError("could not connect")
        if self._private_token != TOKEN:
            raise gitlab.exceptions.GitlabAuthenticationError(
                "could not authenticate token"
            )

    @property
    def user(self):
        return self._owner

    @property
    def tests_only_target_group_id(self):
        return self._target_group_id

    @property
    def groups(self):
        return self._Groups(
            create=self._create_group,
            list=self._list_groups,
            get=self._get_group,
        )

    @property
    def users(self):
        return self._Users(list=self._list_users)

    @property
    def projects(self):
        return self._Projects(
            get=self._get_project, create=self._create_project
        )

    def _get_project(self, full_path):
        if full_path not in self._projects:
            raise gitlab.exceptions.GitlabGetError(
                response_code=404, error_message="Project Not Found"
            )
        return self._projects[full_path]

    def _create_project(self, data):
        """Note thate the self._projects dict is indexed by full path, as
        opposed to id!
        """
        name = data["name"]
        path = data["path"]
        description = data["description"]
        visibility = data["visibility"]
        namespace_id = data["namespace_id"]

        # ensure namespace exists
        try:
            self._get_group(namespace_id)
        except gitlab.exceptions.GitlabGetError:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=400,
                error_message="{'namespace': ['is not valid'], "
                "'limit_reached': []}",
            )

        # ensure no other project in the namespace has the same path
        if path in [
            p.path
            for p in self._projects.values()
            if p.namespace_id == namespace_id
        ]:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=400,
                error_message="Failed to save project "
                "{:path=>['has already been taken']}",
            )

        id = self._next_id()

        full_path = "{}/{}".format(self._group_endpoint(namespace_id), path)
        http_url = "{}/{}.git".format(self._base_url, full_path)
        self._projects[full_path] = Project(
            id=id,
            name=name,
            path=path,
            description=description,
            visibility=visibility,
            namespace_id=namespace_id,
            http_url=http_url,
        )
        return self._projects[full_path]

    def _group_endpoint(self, group_id):
        """Build a url endpoint for a given group by recursively iterating
        through its parents.
        """
        group = self._groups[group_id]
        if group.parent_id:
            prefix = self._group_endpoint(group.parent_id)
            return "{}/{}".format(prefix, group.path)
        return group.path

    def _next_id(self):
        cur_id = self._id
        self._id += 1
        return cur_id

    def _create_group(self, kwargs):
        name = kwargs["name"]
        path = kwargs["path"]
        parent_id = kwargs.get("parent_id")
        if parent_id and parent_id not in self._groups:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=404, error_message="Group Not found"
            )
        if path in [g.path for g in self._groups.values()]:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=400, error_message="Path has already been taken"
            )

        group_id = self._next_id()
        self._groups[group_id] = Group(
            id=group_id,
            name=name,
            path=path,
            parent_id=parent_id,
            users_read_only=self._users,
        )
        return self._groups[group_id]

    def _list_groups(self, *, id=None, search=None):
        groups = self._groups.values()
        if id:
            groups = filter(lambda g: g.parent_id == id, groups)
        if search:
            groups = filter(lambda g: g.name == search, groups)
        return list(groups)

    def _get_group(self, id):
        if id not in self._groups:
            raise gitlab.exceptions.GitlabGetError(
                response_code=404, error_message="Group Not Found"
            )
        return self._groups[id]

    def _list_users(self, username=None):
        if username:
            return [
                usr for usr in self._users.values() if usr.username == username
            ]
        return list(self._users.values())


BASE_URL = "https://some-host.com"
TOKEN = "3049fplktdufpdl23"
TARGET_GROUP = "repobee-testing"
MASTER_GROUP = "repobee-master"


@pytest.fixture(autouse=True)
def api_mock(mocker):
    return mocker.patch(
        "_repobee.ext.gitlab.gitlab.Gitlab", side_effect=GitLabMock
    )


@pytest.fixture
def api(api_mock):
    yield _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)


@pytest.fixture
def team_names():
    return [str(s) for s in constants.STUDENTS]


def raise_(error):
    def inner(*args, **kwargs):
        raise error

    return inner


class TestEnsureTeamsAndMembers:
    @pytest.mark.parametrize(
        "raised_error,expected_error",
        [
            (
                gitlab.exceptions.GitlabAuthenticationError(response_code=401),
                exception.BadCredentials,
            ),
            (
                gitlab.exceptions.GitlabGetError(response_code=404),
                exception.NotFoundError,
            ),
            (
                gitlab.exceptions.GitlabError(response_code=500),
                exception.APIError,
            ),
        ],
    )
    def test_converts_gitlab_errors_to_repobee_errors(
        self, api_mock, raised_error, expected_error, monkeypatch
    ):
        api_mock.groups.list.side_effect = raise_(raised_error)
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)

        monkeypatch.setattr(GitLabMock, "_list_groups", raise_(raised_error))
        with pytest.raises(expected_error):
            api.ensure_teams_and_members(constants.STUDENTS)

    def test_with_no_pre_existing_groups(self, api_mock):
        """Test that all groups are created correctly when the only existing
        group is the target group.
        """
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_team_names = [team.name for team in constants.STUDENTS]
        assert (
            expected_team_names
        ), "pre-test assert, expected team names should be non-empty"

        # act
        api.ensure_teams_and_members(constants.STUDENTS)

        # assert
        actual_teams = api.get_teams()
        assert sorted([g.name for g in actual_teams]) == sorted(
            expected_team_names
        )
        for team in actual_teams:
            if team.name != TARGET_GROUP:
                assert team.members == [constants.USER, team.name]
            else:
                assert not team.members

    def test_with_multi_student_groups(self, api_mock):
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        num_students = len(constants.STUDENTS)
        teams = [
            plug.Team(members=g1.members + g2.members)
            for g1, g2 in zip(
                constants.STUDENTS[: num_students // 2],
                constants.STUDENTS[num_students // 2 :],
            )
        ]
        expected_teams = [
            plug.Team(
                members=[constants.USER] + t.members,
                # the owner should not be included in the generated name
                name=plug.Team(members=t.members).name,
            )
            for t in teams
        ]

        # act
        api.ensure_teams_and_members(teams)

        # assert
        actual_teams = api.get_teams()
        assert len(actual_teams) == len(expected_teams)
        assert sorted([t.name for t in actual_teams]) == sorted(
            t.name for t in expected_teams
        )
        for actual_team, expected_team in zip(
            sorted(actual_teams), sorted(expected_teams)
        ):
            assert sorted(actual_team.members) == sorted(expected_team.members)

    def test_run_twice(self, team_names):
        """Running the function twice should have the same effect as
        running it once.
        """
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_team_names = [t.name for t in constants.STUDENTS]
        assert (
            expected_team_names
        ), "pre-test assert, expected team names should be non-empty"

        # act
        api.ensure_teams_and_members(constants.STUDENTS)
        api.ensure_teams_and_members(constants.STUDENTS)

        # assert
        actual_teams = api.get_teams()
        assert sorted([g.name for g in actual_teams]) == sorted(
            expected_team_names
        )
        for team in actual_teams:
            if team.name != TARGET_GROUP:
                assert team.members == [constants.USER, team.name]
            else:
                assert not team.members

    def test_respects_permission(self):
        """Test that the permission is correctly decoded into a GitLab-specific
        access level.
        """
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)

        api.ensure_teams_and_members(
            constants.STUDENTS, permission=plug.TeamPermission.PULL
        )

        actual_teams = api.get_teams()
        member_access_levels = [
            member.access_level
            for team in actual_teams
            for member in team.implementation.members.list()
            if member.username != constants.USER
        ]

        assert member_access_levels
        for access_level in member_access_levels:
            assert access_level == gitlab.REPORTER_ACCESS


@pytest.fixture
def master_repo_names():
    return ["task-1", "task-2", "task-3"]


class TestGetRepoUrls:
    def test_get_master_repo_urls(self, master_repo_names):
        """When supplied with only master_repo_names, get_repo_urls should
        return urls for those master repos, expecting them to be in the target
        group.
        """
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_urls = [
            api._insert_auth("{}/{}/{}.git".format(BASE_URL, TARGET_GROUP, mn))
            for mn in master_repo_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(master_repo_names)

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)

    def test_get_master_repo_urls_in_master_group(self, master_repo_names):
        """When supplied with master_repo_names and org_name, the urls
        generated should go to the group named org_name instead of the default
        target group.
        """
        # arrange
        master_group = "master-" + TARGET_GROUP  # guaranteed != TARGET_GROUP
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_urls = [
            api._insert_auth("{}/{}/{}.git".format(BASE_URL, master_group, mn))
            for mn in master_repo_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(
            master_repo_names, org_name=master_group
        )

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)

    def test_get_student_repo_urls(self, master_repo_names):
        """When supplied with the students argument, the generated urls should
        go to the student repos related to the supplied master repos.
        """
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_urls = [
            api._insert_auth(
                "{}/{}/{}/{}.git".format(
                    BASE_URL,
                    TARGET_GROUP,
                    str(student_group),
                    plug.generate_repo_name(str(student_group), mn),
                )
            )
            for student_group in constants.STUDENTS
            for mn in master_repo_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(
            master_repo_names, teams=constants.STUDENTS
        )

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)


class TestCreateRepos:
    @pytest.fixture
    def repos(self, api, master_repo_names):
        """Setup repo tuples along with groups for the repos to be created
        in.
        """
        target_group_id = api._gitlab.tests_only_target_group_id
        groups = [
            api._gitlab.groups.create(
                dict(
                    name=str(group), path=str(group), parent_id=target_group_id
                )
            )
            for group in constants.STUDENTS
        ]
        yield [
            plug.Repo(
                name=plug.generate_repo_name(group.name, master_name),
                description="Student repo",
                private=True,
                team_id=group.id,
            )
            for group in groups
            for master_name in master_repo_names
        ]

    def test_run_once_for_valid_repos(self, api, master_repo_names, repos):
        """Test creating projects directly in the target group, when there are
        no pre-existing projects. Should just succeed.
        """
        expected_urls = api.get_repo_urls(
            master_repo_names, teams=constants.STUDENTS
        )

        actual_urls = api.create_repos(repos)

        assert sorted(expected_urls) == sorted(actual_urls)

    def test_run_twice_for_valid_repos(self, api, master_repo_names, repos):
        """Running create_repos twice should have precisely the same effect as
        runing it once."""
        expected_urls = api.get_repo_urls(
            master_repo_names, teams=constants.STUDENTS
        )

        api.create_repos(repos)
        actual_urls = api.create_repos(repos)

        assert sorted(expected_urls) == sorted(actual_urls)


class TestVerifySettings:
    def test_raises_if_token_is_empty(self):
        with pytest.raises(exception.BadCredentials):
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None, org_name=TARGET_GROUP, base_url=BASE_URL, token=""
            )

    def test_raises_on_failed_connection(self):
        with pytest.raises(exception.APIError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url="https://garbage-url",
                token=TOKEN,
            )

        assert "please check the URL" in str(exc_info.value)

    def test_raises_on_bad_token(self):
        with pytest.raises(exception.BadCredentials) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url=BASE_URL,
                token="wrong-token",
            )

        assert "Could not authenticate token" in str(exc_info.value)

    def test_raises_if_group_cant_be_found(self):
        non_existing_group = "some-garbage-group"
        with pytest.raises(exception.NotFoundError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=non_existing_group,
                base_url=BASE_URL,
                token=TOKEN,
            )

        assert "Could not find group with slug {}".format(
            non_existing_group
        ) in str(exc_info.value)

    def test_raises_if_master_group_cant_be_found(self):
        non_existing_group = "some-garbage-group"
        with pytest.raises(exception.NotFoundError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url=BASE_URL,
                token=TOKEN,
                master_org_name=non_existing_group,
            )

        assert "Could not find group with slug {}".format(
            non_existing_group
        ) in str(exc_info.value)

    def test_happy_path(self, mocker):
        """Test that the great success message is printed if all is as it
        should.
        """
        gl = GitLabMock(BASE_URL, TOKEN, False)
        gl.groups.create(dict(name=MASTER_GROUP, path=MASTER_GROUP))
        mocker.patch(
            "_repobee.ext.gitlab.gitlab.Gitlab",
            side_effect=lambda base_url, private_token, ssl_verify: gl,
        )
        log_mock = mocker.patch("_repobee.ext.gitlab.LOGGER")

        _repobee.ext.gitlab.GitLabAPI.verify_settings(
            user=None,
            org_name=TARGET_GROUP,
            base_url=BASE_URL,
            token=TOKEN,
            master_org_name=MASTER_GROUP,
        )

        log_mock.info.assert_called_with(
            "GREAT SUCCESS: All settings check out!"
        )


class TestDeleteTeams:
    @pytest.fixture
    def groups(self, api):
        api.ensure_teams_and_members(constants.STUDENTS)
        return [g for g in api._gitlab.groups.list() if g.name != TARGET_GROUP]

    def test_delete_teams_that_dont_exist(self, api, groups):
        """It should have no effect."""

        api.delete_teams(["some", "non-existing", "teams"])

        num_deleted = 0
        for group in groups:
            assert not group.tests_only_deleted
            num_deleted += 1
        assert num_deleted == len(groups)

    def test_delete_all_existing_teams(self, api, groups):
        team_names = [g.name for g in groups]

        api.delete_teams(team_names)

        for group in groups:
            assert group.tests_only_deleted

    def test_delete_some_existing_teams(self, api, groups):
        team_names = [
            g.name for g in groups[len(groups) // 3 : len(groups) // 2]
        ]
        expected_num_deleted = len(team_names)
        # +1 for the target group
        expected_num_not_deleted = len(constants.STUDENTS) - len(team_names)

        api.delete_teams(team_names)

        deleted = 0
        not_deleted = 0
        for group in groups:
            if group.name == TARGET_GROUP:
                continue
            elif group.name in team_names:
                assert group.tests_only_deleted
                deleted += 1
            else:
                assert not group.tests_only_deleted
                not_deleted += 1

        assert deleted == expected_num_deleted
        assert not_deleted == expected_num_not_deleted
