from collections import namedtuple

import pytest
import gitlab

import constants

import repobee


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
    _User = namedtuple("_User", ("id", "username"))
    _Projects = namedtuple("_Projects", "create get".split())

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

        # this is only for testing purposes, does not exist in the real class
        self._target_group_id = list(self._groups.keys())[0]

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


class TestCreateRepos:
    @pytest.fixture
    def api(self, api_mock):
        yield repobee.gitlab_api.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)

    @pytest.fixture
    def master_repo_names(self):
        return ["task-1", "task-2", "task-3"]

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
            repobee.tuples.Repo(
                name=repobee.util.generate_repo_name(group.name, master_name),
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
            master_repo_names, students=constants.STUDENTS
        )

        actual_urls = api.create_repos(repos)

        assert sorted(expected_urls) == sorted(actual_urls)

    def test_run_twice_for_valid_repos(self, api, master_repo_names, repos):
        """Running create_repos twice should have precisely the same effect as
        runing it once."""
        expected_urls = api.get_repo_urls(
            master_repo_names, students=constants.STUDENTS
        )

        api.create_repos(repos)
        actual_urls = api.create_repos(repos)

        assert sorted(expected_urls) == sorted(actual_urls)
