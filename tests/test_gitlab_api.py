from collections import namedtuple

import pytest
import gitlab

import constants

import repobee


class Group:
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
        self._users_read_only = users_read_only

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


class GitLabMock:
    """Class representing a GitLab instance, with the subset of functionality
    required for RepoBee to work. It may seem counterintuitive to create this
    much logic to test a class, but from experience it became much more
    complicated to try to mock out individual pieces, when those individual
    pieces exhibit interconnected behavior.
    """

    _Groups = namedtuple("_Groups", ("create", "list", "get"))
    _Users = namedtuple("_Users", ("list"))
    _User = namedtuple("_User", ("id", "username"))
    _Project = namedtuple(
        "_Project", "id name path description visibility namespace_id".split()
    )
    _Projects = namedtuple("_Projects", "create get attributes".split())

    def __init__(self, url, private_token):
        self._base_url = url
        self._private_token = private_token
        self._groups = {}
        self._projects = {}
        self._users = {
            id: self._User(id=id, username=str(grp))
            for id, grp in enumerate(constants.STUDENTS)
        }
        self._id = len(self._users)
        self._create_group({"name": TARGET_GROUP, "path": TARGET_GROUP})

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
            raise gitlab.exceptions.GitlabCreateError(
                response_code=404, error_message="Group Not found"
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


@pytest.fixture(autouse=True)
def api_mock(mocker):
    mocker.patch("repobee.gitlab_api.gitlab.Gitlab", side_effect=GitLabMock)


@pytest.fixture
def team_names():
    return [str(s) for s in constants.STUDENTS]


class TestEnsureTeamsAndMembers:
    def test_with_no_pre_existing_groups(self, api_mock, team_names):
        """Test that all groups are created correctly when the only existing
        group is the target group.
        """
        # arrange
        api = repobee.gitlab_api.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        allocations = {tn: [tn] for tn in team_names}
        expected_group_names = list(allocations.keys())
        assert (
            expected_group_names
        ), "pre-test assert, expected group names should be non-empty"

        # act
        api.ensure_teams_and_members(allocations)

        # assert
        actual_groups = api.get_teams()
        assert sorted([g.name for g in actual_groups]) == sorted(
            expected_group_names
        )
        for group in actual_groups:
            if group.name != TARGET_GROUP:
                group_member_names = [m.username for m in group.members.list()]
                assert group_member_names == [group.name]
            else:
                assert not group.members.list()

    def test_with_multi_student_groups(self, api_mock):
        # arrange
        api = repobee.gitlab_api.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        num_students = len(constants.STUDENTS)
        allocations = {
            str(
                repobee.tuples.Group(members=g1.members + g2.members)
            ): g1.members
            + g2.members
            for g1, g2 in zip(
                constants.STUDENTS[: num_students // 2],
                constants.STUDENTS[num_students // 2 :],
            )
        }
        expected_groups = dict(allocations)

        # act
        api.ensure_teams_and_members(allocations)

        # assert
        actual_groups = api.get_teams()
        assert len(actual_groups) == len(expected_groups)
        assert sorted([g.name for g in actual_groups]) == sorted(
            expected_groups.keys()
        )
        for group in actual_groups:
            member_names = [m.username for m in group.members.list()]
            expected_member_names = expected_groups[group.name]
            assert sorted(member_names) == sorted(expected_member_names)

    def test_run_twice(self, team_names):
        """Running the function twice should have the same effect as
        running it once.
        """
        # arrange
        api = repobee.gitlab_api.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        allocations = {tn: [tn] for tn in team_names}
        expected_group_names = list(allocations.keys())
        assert (
            expected_group_names
        ), "pre-test assert, expected group names should be non-empty"

        # act
        api.ensure_teams_and_members(allocations)
        api.ensure_teams_and_members(allocations)

        # assert
        actual_groups = api.get_teams()
        assert sorted([g.name for g in actual_groups]) == sorted(
            expected_group_names
        )
        for group in actual_groups:
            if group.name != TARGET_GROUP:
                group_member_names = [m.username for m in group.members.list()]
                assert group_member_names == [group.name]
            else:
                assert not group.members.list()
