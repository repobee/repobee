from collections import namedtuple
import itertools
import unittest.mock

import requests.exceptions
import pytest
import gitlab
import repobee_plug as plug

import _repobee

import constants

PAGE_SIZE = 10


class Group:
    """Class mimicking a gitlab.Group"""

    _Members = namedtuple("_Members", ("create", "list"))
    _Member = namedtuple("_Member", ("id", "access_level", "username"))
    _Projects = namedtuple("_Projects", "list")

    def __init__(self, id, name, path, parent_id, users_read_only):
        self.id = id
        self.name = name
        self.path = path
        self.parent_id = parent_id
        self.members = self._Members(
            create=self._create_member, list=self._list_members
        )
        self._member_list = []
        self._project_list = []
        self._group_list = []
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

    def _list_members(self, all=False):
        return list(self._member_list)[: (PAGE_SIZE if not all else None)]

    def _list_projects(self, all=False, include_subgroups=False):
        projects = list(self._project_list)

        if include_subgroups:
            projects += list(
                itertools.chain.from_iterable(
                    [list(g._project_list) for g in self._group_list]
                )
            )
        return projects[: (PAGE_SIZE if not all else None)]

    def delete(self):
        self._deleted = True

    @property
    def tests_only_deleted(self):
        return self._deleted

    @property
    def projects(self):
        return self._Projects(list=self._list_projects)


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
        self._user = self._owner
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
        return self._user

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

    def _get_project(self, full_path_or_id):
        if full_path_or_id in self._projects:
            return self._projects[full_path_or_id]

        for project in self._projects.values():
            if project.id == full_path_or_id:
                return project

        raise gitlab.exceptions.GitlabGetError(
            response_code=404, error_message="Project Not Found"
        )

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
            group = self._get_group(namespace_id)
        except gitlab.exceptions.GitlabGetError:
            raise gitlab.exceptions.GitlabCreateError(
                response_code=400,
                error_message="{'namespace': ['is not valid'], "
                "'limit_reached': []}",
            )

        # ensure no other project in the namespace has the same path
        if path in [p.path for p in group.projects.list(all=True)]:
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
        group._project_list.append(self._projects[full_path])
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

        if parent_id:
            self._groups[parent_id]._group_list.append(self._groups[group_id])

        return self._groups[group_id]

    def _list_groups(self, *, id=None, search=None, all=False):
        groups = self._groups.values()
        if id:
            groups = filter(lambda g: g.parent_id == id, groups)
        if search:
            groups = filter(lambda g: g.name == search, groups)
        return list(groups)[: (PAGE_SIZE if not all else None)]

    def _get_group(self, id):
        if id in self._groups:
            return self._groups[id]

        for gid, group in self._groups.items():
            if group.path == id:
                return group

        raise gitlab.exceptions.GitlabGetError(
            response_code=404, error_message="Group Not Found"
        )

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


@pytest.fixture
def repo_names(api, assignment_names):
    """Setup repo tuples along with groups for the repos to be created in."""
    target_group_id = api._gitlab.tests_only_target_group_id
    groups = [
        api._gitlab.groups.create(
            dict(name=str(team), path=str(team), parent_id=target_group_id)
        )
        for team in constants.STUDENTS
    ]

    repo_names = []
    for group, assignment in itertools.product(groups, assignment_names):
        repo_name = plug.generate_repo_name(group.name, assignment)
        api._gitlab.projects.create(
            dict(
                name=repo_name,
                path=repo_name,
                description="Some description",
                visibility="private",
                namespace_id=group.id,
            )
        )
        repo_names.append(repo_name)
    return repo_names


class TestInit:
    """Tests for the GitLabAPI constructor."""

    def test_raises_api_error_when_target_group_cant_be_found(self):
        with pytest.raises(plug.NotFoundError):
            _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, "fake-name")


@pytest.fixture
def assignment_names():
    return ["task-1", "task-2", "task-3"]


class TestGetRepoUrls:
    def test_get_template_repo_urls(self, assignment_names):
        """When supplied with only assignment_names, get_repo_urls should
        return urls for those master repos, expecting them to be in the target
        group.
        """
        # arrange
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_urls = [
            api._insert_auth("{}/{}/{}.git".format(BASE_URL, TARGET_GROUP, mn))
            for mn in assignment_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(assignment_names, insert_auth=True)

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)

    def test_get_template_repo_urls_in_master_group(self, assignment_names):
        """When supplied with assignment_names and org_name, the urls
        generated should go to the group named org_name instead of the default
        target group.
        """
        # arrange
        master_group = "master-" + TARGET_GROUP  # guaranteed != TARGET_GROUP
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)
        expected_urls = [
            api._insert_auth("{}/{}/{}.git".format(BASE_URL, master_group, mn))
            for mn in assignment_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(
            assignment_names, org_name=master_group, insert_auth=True
        )

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)

    def test_get_student_repo_urls(self, assignment_names):
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
            for mn in assignment_names
        ]
        assert (
            expected_urls
        ), "there must be at least some urls for this test to make sense"

        # act
        actual_urls = api.get_repo_urls(
            assignment_names,
            team_names=[t.name for t in constants.STUDENTS],
            insert_auth=True,
        )

        # assert
        assert sorted(actual_urls) == sorted(expected_urls)


class TestDeleteRepo:
    """Tests for delete_repo."""

    def test_delete_repo_calls_correct_function(self):
        # arrange
        platform_repo_mock = unittest.mock.MagicMock()
        repo = plug.Repo(
            name="some-repo",
            description="a repo",
            private=True,
            url="doesntmatter",
            implementation=platform_repo_mock,
        )
        api = _repobee.ext.gitlab.GitLabAPI(BASE_URL, TOKEN, TARGET_GROUP)

        # act
        api.delete_repo(repo)

        # assert
        platform_repo_mock.delete.assert_called_once()


class TestGetRepos:
    """Tests for get_repos."""

    def test_get_all_repos(self, api, repo_names):
        """get_repos should return all repos when called without an
        argument.
        """
        assert len(list(api.get_repos())) == len(repo_names)


class TestInsertAuth:
    """Tests for insert_auth."""

    def test_inserts_into_https_url(self, api):
        url = f"{BASE_URL}/some/repo"
        authed_url = api.insert_auth(url)
        assert authed_url.startswith(f"https://oauth2:{TOKEN}")

    def test_raises_on_non_platform_url(self, api):
        url = "https://somedomain.com"

        with pytest.raises(plug.InvalidURL) as exc_info:
            api.insert_auth(url)

        assert "url not found on platform" in str(exc_info.value)


class TestVerifySettings:
    def test_raises_if_token_is_empty(self):
        with pytest.raises(plug.BadCredentials):
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None, org_name=TARGET_GROUP, base_url=BASE_URL, token=""
            )

    def test_raises_on_failed_connection(self):
        with pytest.raises(plug.PlatformError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url="https://garbage-url",
                token=TOKEN,
            )

        assert "please check the URL" in str(exc_info.value)

    def test_raises_on_bad_token(self):
        with pytest.raises(plug.BadCredentials) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url=BASE_URL,
                token="wrong-token",
            )

        assert "Could not authenticate token" in str(exc_info.value)

    def test_raises_if_group_cant_be_found(self):
        non_existing_group = "some-garbage-group"
        with pytest.raises(plug.NotFoundError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=non_existing_group,
                base_url=BASE_URL,
                token=TOKEN,
            )

        assert non_existing_group in str(exc_info.value)

    def test_raises_if_master_group_cant_be_found(self):
        non_existing_group = "some-garbage-group"
        with pytest.raises(plug.NotFoundError) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url=BASE_URL,
                token=TOKEN,
                template_org_name=non_existing_group,
            )

        assert non_existing_group in str(exc_info.value)

    def test_raises_when_user_is_not_member(self, mocker):
        gl = GitLabMock(BASE_URL, TOKEN, False)
        gl.groups.create(dict(name=MASTER_GROUP, path=MASTER_GROUP))
        user = User(id=9999, username="some-random-user")
        gl._user = user
        mocker.patch(
            "_repobee.ext.gitlab.gitlab.Gitlab",
            side_effect=lambda base_url, private_token, ssl_verify: gl,
        )

        with pytest.raises(plug.BadCredentials) as exc_info:
            _repobee.ext.gitlab.GitLabAPI.verify_settings(
                user=None,
                org_name=TARGET_GROUP,
                base_url=BASE_URL,
                token=TOKEN,
                template_org_name=MASTER_GROUP,
            )

        assert f"{user.username} is not a member of {TARGET_GROUP}" in str(
            exc_info.value
        )

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
        log_mock = mocker.patch("repobee_plug.log.info")

        _repobee.ext.gitlab.GitLabAPI.verify_settings(
            user=None,
            org_name=TARGET_GROUP,
            base_url=BASE_URL,
            token=TOKEN,
            template_org_name=MASTER_GROUP,
        )

        log_mock.assert_called_with("GREAT SUCCESS: All settings check out!")
