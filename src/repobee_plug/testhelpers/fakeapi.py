"""A faked implementation of the :py:class:`repobee_plug.API` specification
that can be used to test RepoBee and plugins.

.. danger::

    This module is in alpha version, and its behavior may change without
    notice.
"""

import re
import itertools
import pathlib
import collections
import git
import pickle
import datetime
from typing import List, Iterable, Any, Optional, Tuple

import repobee_plug as plug

TIME = datetime.datetime.now().isoformat()

_User = collections.namedtuple("_User", "username")


class _Issue:
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


class _Repo:
    def __init__(
        self,
        name: str,
        description: str,
        team_id: Any,
        url: str,
        private: bool,
    ):
        self.name = name
        self.description = description
        self.url = url
        self.team_id = team_id
        self.private = private
        self.issues = []

    def to_plug_repo(self) -> plug.Repo:
        return plug.Repo(
            name=self.name,
            description=self.description,
            private=self.private,
            team_id=self.team_id,
            url=self.url,
            implementation=self,
        )

    @staticmethod
    def gen_id(repo_name: str, org_name: str) -> str:
        return f"{org_name}/{repo_name}"


class _Team:
    def __init__(
        self,
        name: str,
        members: List[_User],
        permission: plug.TeamPermission,
        id: str,
        repos: List[_Repo] = None,
    ):
        self.name = name
        self.members = members
        self.permission = permission
        self.repos = repos or []
        self.id = id

    def to_plug_team(self) -> plug.Team:
        return plug.Team(
            name=self.name,
            members=[mem.username for mem in self.members],
            id=self.id,
            implementation=self,
        )

    @staticmethod
    def gen_id(team_name: str, org_name: str) -> str:
        return f"{org_name}/{team_name}"


class FakeAPI(plug.API):
    """A fake implementation of the :py:class:`repobee_plug.API` specification,
    which emulates a GitHub-like platform.
    """

    def __init__(self, base_url: str, org_name: str, user: str):
        self._repodir = pathlib.Path(base_url[len("https://") :])
        self._org_name = org_name
        self._user = user

        self._teams = {}
        self._repos = {}
        self._users = {}

    def ensure_teams_and_members(
        self,
        teams: Iterable[plug.Team],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> List[plug.Team]:
        return [
            self._ensure_team_exists(team, permission).to_plug_team()
            for team in teams
        ]

    def get_teams(self) -> List[plug.Team]:
        return [team.to_plug_team() for team in self._teams.values()]

    def create_repos(self, repos: Iterable[plug.Repo]) -> List[str]:
        return [self._ensure_repo_exists(repo).url for repo in repos]

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

    def get_issues(
        self,
        repo_names: Iterable[str],
        state: plug.IssueState = plug.IssueState.OPEN,
        title_regex: str = "",
    ) -> Iterable[Tuple[str, Iterable[plug.Issue]]]:
        repos = self._get_repos_by_name(repo_names)
        for repo in repos:
            issues = [
                issue.to_plug_issue()
                for issue in repo.issues
                if re.match(title_regex, issue.title)
                and state == plug.IssueState.ALL
                or issue.state == state
            ]
            yield repo.name, issues

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        repos = self._get_repos_by_name(repo_names)
        for repo in repos:
            issue = _Issue(
                title=title,
                body=body,
                number=len(repo.issues),
                created_at=TIME,
                author=self._user,
                state=plug.IssueState.OPEN,
            )
            repo.issues.append(issue)

    def close_issue(self, title_regex: str, repo_names: Iterable[str]):
        repos = self._get_repos_by_name(repo_names)
        all_issues = itertools.chain.from_iterable(
            repo.issues for repo in repos
        )
        for issue in all_issues:
            if re.match(title_regex, issue.title):
                issue.state = plug.IssueState.CLOSED

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ) -> None:
        pass

    def _set_repodir(self, basedir: pathlib.Path) -> None:
        self._restore_state()

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

    def _get_team(self, team_id: str) -> _Team:
        if team_id not in self._teams:
            raise plug.NotFoundError(f"invalid team id: {team_id}")
        return self._teams[team_id]

    def _get_repo(
        self,
        repo_name: str,
        org_name: Optional[str] = None,
        strict: bool = False,
    ) -> _Repo:
        repo_id = _Repo.gen_id(repo_name, org_name or self._org_name)
        if repo_id not in self._repos:
            raise plug.NotFoundError(f"no such repo: {repo_id}")
        return self._repos[repo_id]

    def _get_repos_by_name(self, repo_names: Iterable[str]) -> List[_Repo]:
        """Get repos from the current organization that match
        any of the names in ``repo_names``. Unmatched names are
        ignored.
        """
        unfiltered_repos = (
            self._repos[_Repo.gen_id(name, self._org_name)]
            for name in repo_names
        )
        return [repo for repo in unfiltered_repos if repo]

    def _ensure_team_exists(
        self, team: plug.Team, permission: plug.TeamPermission
    ) -> _Team:
        team_id = _Team.gen_id(team_name=team.name, org_name=self._org_name)
        requested_members = [
            self._get_user(username)
            for username in team.members
            if username in self._users
        ]
        stored_team = self._teams.setdefault(
            team_id,
            _Team(
                name=team.name,
                members=requested_members,
                permission=permission,
                id=team_id,
            ),
        )
        stored_team.members = list(
            set(requested_members) | set(stored_team.members)
        )

        return self._teams[team_id]

    def _ensure_repo_exists(self, repo: plug.Repo) -> _Repo:
        repo_id = _Repo.gen_id(repo.name, self._org_name)
        if repo_id not in self._repos:
            repo_path = self._repodir / self._org_name / repo.name
            repo_path.mkdir(parents=True, exist_ok=True)
            git.Repo.init(repo_path, bare=True)
            self._repos[repo_id] = _Repo(
                name=repo.name,
                description=repo.description,
                url=repo_path.as_uri(),
                # call self._get_team to ensure that the taem
                # actually exists
                team_id=self._get_team(repo.team_id).id,
                private=repo.private,
            )

        return self._repos[repo_id]


class FakeAPIHooks(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "org_name", "user")

    def get_api_class(self):
        return FakeAPI
