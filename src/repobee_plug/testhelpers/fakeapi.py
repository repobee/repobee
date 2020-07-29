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
from typing import List, Iterable, Any, Optional

import repobee_plug as plug

_User = collections.namedtuple("_User", "username")


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

    def to_plug_repo(self) -> plug.Repo:
        return plug.Repo(
            name=self.name,
            description=self.description,
            private=self.private,
            team_id=self.team_id,
            url=self.url,
            implementation=self,
        )


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

    def __init__(self, base_url: str, token: str, org_name: str, user: str):
        self._base_url = base_url
        self._token = token
        self._org_name = org_name
        self._user = user

        self._teams = {}
        self._repos = {}
        self._users = {}

        self.__repodir = None
        self._set_repodir(pathlib.Path("/home/slarse/tmp/repos"))
        self._add_users("simon alice eve".split())

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

    def _set_repodir(self, basedir: pathlib.Path) -> None:
        self.__repodir = basedir
        self._restore_state()

    @property
    def _repodir(self):
        if not self.__repodir:
            raise RuntimeError(
                f"The '{self.__class__.__name__}' repodir has not been set. "
                f"Set it with '{self._set_repodir.__name__}'."
            )
        return self.__repodir

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

    def _get_user(self, username: str) -> _User:
        if username not in self._users:
            raise plug.NotFoundError(f"no such user: {username}")
        return self._users[username]

    def _get_team(self, team_id: str) -> _Team:
        if team_id not in self._teams:
            raise plug.NotFoundError(f"invalid team id: {team_id}")
        return self._teams[team_id]

    def _get_repo(self, repo_name: str, org_name: str) -> _Team:
        repo_id = f"{self._org_name}/{repo_name}"
        if repo_id not in self._repos:
            raise plug.NotFoundError(f"no such repo: {repo_id}")
        return self._repos[repo_id]

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
        repo_id = f"{self._org_name}/{repo.name}"
        if repo_id not in self._repos:
            repo_path = self._repodir / self._org_name / repo.name
            repo_path.mkdir(parents=True)
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


class FakeApiHooks(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "token", "org_name", "user")

    def get_api_class(self):
        return FakeAPI
