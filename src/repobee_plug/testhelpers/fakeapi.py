"""A faked implementation of the :py:class:`repobee_plug.API` specification
that can be used to test RepoBee and plugins.

.. danger::

    This module is in alpha version, and its behavior may change without
    notice.
"""

import pathlib
import collections
import git
import pickle
import datetime
from typing import List, Iterable, Any, Optional, Tuple

import repobee_plug as plug

TIME = datetime.datetime.now().isoformat()

_User = collections.namedtuple("_User", "username")


class Issue:
    def __init__(
        self,
        title: str,
        body: str,
        number: int,
        created_at: str,
        author: str,
        state: plug.IssueState,
    ):
        self.title = title
        self.body = body
        self.number = number
        self.created_at = created_at
        self.author = author
        self.state = state

    def to_plug_issue(self):
        return plug.Issue(
            title=self.title,
            body=self.body,
            number=self.number,
            created_at=self.created_at,
            author=self.author,
            implementation=self,
        )


class Repo:
    def __init__(
        self,
        name: str,
        description: str,
        team_id: Any,
        url: str,
        private: bool,
        path: pathlib.Path,
    ):
        self.name = name
        self.description = description
        self.url = url
        self.team_id = team_id
        self.private = private
        self.issues = []
        self.path = path

    def to_plug_repo(self, include_issues=None) -> plug.Repo:
        issues = [
            issue.to_plug_issue()
            for issue in self.issues
            if issue.state == include_issues
        ] or None
        return plug.Repo(
            name=self.name,
            description=self.description,
            private=self.private,
            team_id=self.team_id,
            url=self.url,
            issues=issues,
            implementation=self,
        )


class Team:
    def __init__(
        self,
        name: str,
        members: List[_User],
        permission: plug.TeamPermission,
        id: str,
        repos: List[Repo] = None,
    ):
        self.name = name
        self.members = members
        self.permission = permission
        self.repos = repos or []
        self.id = id

    def add_members(self, users: List[_User]) -> None:
        self.members = list(set(self.members) | set(users))

    def to_plug_team(self) -> plug.Team:
        return plug.Team(
            name=self.name,
            members=[mem.username for mem in self.members],
            id=self.id,
            implementation=self,
        )


class FakeAPI(plug.API):
    """A fake implementation of the :py:class:`repobee_plug.API` specification,
    which emulates a GitHub-like platform.
    """

    def __init__(self, base_url: str, org_name: str, user: str):
        self._repodir = pathlib.Path(base_url[len("https://") :])
        self._org_name = org_name
        self._user = user

        self._teams = {self._org_name: {}}
        self._repos = {self._org_name: {}}
        self._users = {}
        self._restore_state()

    # START EXPERIMENTAL API
    def create_team(
        self,
        name: str,
        members: Optional[List[str]] = None,
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> plug.Team:
        stored_team = self._teams[self._org_name].setdefault(
            name, Team(name=name, members=[], permission=permission, id=name)
        )
        return self.assign_members(
            stored_team.to_plug_team(), members or [], permission
        )

    def assign_members(
        self,
        team: plug.Team,
        members: List[str],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> plug.Team:
        team.implementation.add_members(
            [self._get_user(m) for m in members or []]
        )
        return team.implementation.to_plug_team()

    def create_repo(
        self,
        name: str,
        description: str,
        private: bool,
        team: Optional[plug.Team] = None,
    ) -> plug.Repo:
        assert not team or team.implementation

        repo_bucket = self._repos.setdefault(self._org_name, {})
        team_id = self._get_team(team.id).id if team else None
        if name not in repo_bucket:
            repo_path = self._repodir / self._org_name / name
            repo_path.mkdir(parents=True, exist_ok=True)
            git.Repo.init(repo_path, bare=True)
            repo_bucket[name] = Repo(
                name=name,
                description=description,
                url=repo_path.as_uri(),
                # call self._get_team to ensure that the team
                # actually exists
                team_id=self._get_team(team_id).id,
                private=private,
                path=repo_path,
            )

        return self._repos[self._org_name][name].to_plug_repo()

    def get_teams_(
        self,
        team_names: Optional[List[str]] = None,
        include_repos: bool = False,
    ) -> Iterable[plug.Team]:
        team_names = set(team_names or [])
        return [
            team.to_plug_team()
            for team in self._teams[self._org_name].values()
            if not team_names or team.name in team_names
        ]

    def get_repos(
        self,
        repo_names: Optional[List[str]] = None,
        include_issues: Optional[plug.IssueState] = None,
    ) -> Iterable[plug.Repo]:
        unfiltered_repos = (
            self._repos[self._org_name].get(name) for name in repo_names
        )
        return [
            repo.to_plug_repo(include_issues)
            for repo in unfiltered_repos
            if repo
        ]

    def insert_auth(self, url: str) -> str:
        return url

    def create_issue(
        self,
        title: str,
        body: str,
        repo: plug.Repo,
        assignees: Optional[str] = None,
    ) -> Tuple[Repo, Issue]:
        assert not assignees
        issue = Issue(
            title=title,
            body=body,
            number=len(repo.implementation.issues),
            created_at=TIME,
            author=self._user,
            state=plug.IssueState.OPEN,
        )
        repo.implementation.issues.append(issue)
        return repo.implementation.to_plug_repo(), issue.to_plug_issue()

    def close_issue_(self, issue: Issue) -> Issue:
        issue.implementation.state = plug.IssueState.CLOSED
        return issue.implementation.to_plug_issue()

    # END EXPERIMENTAL API

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[plug.Team]] = None,
    ) -> List[str]:
        base = self._repodir / (org_name or self._org_name)
        repo_names = (
            master_repo_names
            if not teams
            else plug.generate_repo_names(teams, master_repo_names)
        )
        return [(base / name).as_uri() for name in repo_names]

    def extract_repo_name(self, repo_url: str) -> str:
        return pathlib.Path(repo_url).stem

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ) -> None:
        pass

    def __getattribute__(self, key):
        attr = object.__getattribute__(self, key)

        if (
            not key.startswith("_")
            and hasattr(plug.API, key)
            and callable(attr)
        ):
            # automatically save state after each API call

            def _func(*args, **kwargs):
                res = attr(*args, **kwargs)
                self._save_state()
                return res

            return _func

        return attr

    def _save_state(self):
        pickle_path = self._repodir / "state.pickle"
        pickle_path.write_bytes(pickle.dumps(self))

    def _restore_state(self):
        pickle_path = self._repodir / "state.pickle"
        if pickle_path.is_file():
            state = pickle.loads(pickle_path.read_bytes())
            self.__dict__ = state.__dict__

    def _add_users(self, usernames: List[str]) -> None:
        """Add users to this instance.

        .. note::

            This function is public for use in testing.

        Args:
            usernames: A list of usernames to add.
        """
        self._users.update({name: _User(name) for name in usernames})
        self._save_state()

    def _get_user(self, username: str) -> _User:
        if username not in self._users:
            raise plug.NotFoundError(f"no such user: {username}")
        return self._users[username]

    def _get_team(self, team_id: str) -> Team:
        if team_id not in self._teams[self._org_name]:
            raise plug.NotFoundError(f"invalid team id: {team_id}")
        return self._teams[self._org_name][team_id]


class FakeAPIHooks(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "org_name", "user")

    def get_api_class(self):
        return FakeAPI
