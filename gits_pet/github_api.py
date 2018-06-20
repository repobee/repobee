"""Wrapper module for the GitHub API.

This module currently wraps PyGithub commands. The purpose of the module is to
make it easy to swap out PyGithub at a later date.

.. important: The setup_api function _must_ be called before any functions in
this module are called.

"""
import contextlib
import collections
from typing import List, Iterable, Mapping
import daiquiri
import github

LOGGER = daiquiri.getLogger(__file__)

# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository

# classes also used externally
Team = collections.namedtuple('Team', ('name', 'members', 'id'))
RepoInfo = collections.namedtuple(
    'RepoInfo', ('name', 'description', 'private', 'team_id'))


class GitHubError(Exception):
    """An exception raised when the API responds with an error code."""

    def __init__(self, msg=None, status=None):
        self.status = status
        super().__init__(self, msg)


class NotFoundError(GitHubError):
    """An exception raised when the API responds with a 404."""


class UnexpectedException(GitHubError):
    """An exception raised when an API request raises an unexpected exception."""


@contextlib.contextmanager
def _try_api_request():
    """Context manager for trying API requests."""
    try:
        yield
    except github.GithubException as e:
        if e.status == 404:
            raise NotFoundError(str(e), status=404)
        else:
            raise GitHubError(str(e), status=e.status)
    except Exception as e:
        raise UnexpectedException("An unexpected exception occured. This is "
                                  "probably a bug, please report it.")


class _ApiWrapper:
    """A wrapper class for a GitHub API. Currently wraps PyGithub."""

    def __init__(self, base_url: str, token: str, org_name: str):
        """
        Args:
            base_url: The base url to a GitHub REST api (e.g.
            https://api.github.com for GitHub or https://<HOST>/api/v3 for
            Enterprise).
            token: A GitHub OAUTH token.
            org_name: Name of an organization.
        """
        self._github = github.Github(login_or_token=token, base_url=base_url)
        with _try_api_request():
            self._org = self._github.get_organization(org_name)

    def get_user(self, username) -> _User:
        """Get a user from the organization.
        
        Args:
            username: A username.
            
        Returns:
            A _User object.
        """
        with _try_api_request():
            return self._github.get_user(username)

    def get_teams(self) -> Iterable[_Team]:
        """Returns: An iterable of the organization's teams."""
        with _try_api_request():
            return self._org.get_teams()

    def add_to_team(self, member: _User, team: _Team):
        """Add a user to a team.

        Args:
            member: A user to add to the team.
            team: A _Team.
        """
        with _try_api_request():
            team.add_membership(member)

    def get_repo_url(self, repo_name: str) -> _Repo:
        """Get a repo from the organization.
        
        Args:
            repo_name: Name of a repo.
        """
        with _try_api_request():
            return self._org.get_repo(repo_name).html_url

    def create_repo(self, repo_info: RepoInfo):
        """Create a repo in the organization.

        Args:
            repo_info: Repo attributes.

        Returns:
            The html url to the repo.
        """
        with _try_api_request():
            repo = self._org.create_repo(
                repo_info.name,
                description=repo_info.description,
                private=repo_info.private,
                team_id=repo_info.team_id)
        return repo.html_url

    def create_team(self, team_name: str, permission: str = 'push') -> _Team:
        """Create a team in the organization.

        Args:
            team_name: Name for the team.
            permission: The default access permission of the team.

        Returns:
            The created team.
        """
        with _try_api_request():
            team = self._org.create_team(team_name, permission=permission)
        return team

    @property
    def org_name(self):
        """Returns: Name of the organization."""
        return self._org.name


class GitHubAPI:
    """A highly specialized GitHub API class for gits_pet."""

    def __init__(self, base_url: str, token: str, org_name: str):
        """Set up the GitHub API object. Must be called before any of the functions
        in this module are called!

        Args:
            base_url: The base url to a GitHub REST api (e.g.
            https://api.github.com for GitHub or https://<HOST>/api/v3 for
            Enterprise).
            token: A GitHub OAUTH token.
            org_name: Name of an organization.
        """
        self._api = _ApiWrapper(base_url, token, org_name)

    def _ensure_teams_exist(
            self, team_names: Iterable[str]) -> List[github.Team.Team]:
        """Ensure that teams with the given team names exist in the given
        organization. Create any that do not.
        
        Args:
            team_names: An iterable of team names.

        Returns:
            A list of Team namedtuples representing the teams corresponding to the
            provided team_names.
        """
        existing_team_names = set(team.name for team in self._api.get_teams())

        required_team_names = set(team_names)
        for team_name in required_team_names - existing_team_names:
            try:
                self._api.create_team(team_name, permission='push')
                LOGGER.info("created team {}".format(team_name))
            except GitHubError as exc:
                if exc.status != 422:
                    raise UnexpectedException(str(exc))
                LOGGER.info("team {} already exists".format(team_name))

        teams = [
            team for team in self._api.get_teams()
            if team.name in required_team_names
        ]
        return teams

    def ensure_teams_and_members(
            self, member_lists: Mapping[str, Iterable[str]]) -> List[Team]:
        """Ensure that each team exists and has its required members. If a team is
        does not exist or is missing any of the members in its member list, the team
        is created and/or missing members are added. Otherwise, nothing happens.

        Args:
            member_list: A mapping of (team_name, member_list) mappings.

        Returns:
            A list of Team namedtuples of the teams corresponding to the keys of
            the member_lists mapping.
        """
        LOGGER.info("creating teams...")
        teams = self._ensure_teams_exist(
            [team_name for team_name in member_lists.keys()])

        LOGGER.info("adding members to teams...")
        for team in teams:
            self._ensure_members_in_team(team, member_lists[team.name])

        with _try_api_request():
            team_wrappers = [
                Team(
                    name=team.name,
                    members=[m.name for m in team.get_members()],
                    id=team.id) for team in teams
            ]
        return team_wrappers

    def _ensure_members_in_team(self, team: _Team, members: Iterable[str]):
        """Add all of the users in 'memebrs' to a team. Skips any users that
        don't exist, or are already in the team.

        Args:
            team: A _Team object to which members should be added.
            members: An iterable of usernames.
        """
        required_members = set(members)
        existing_members = set(team.get_members())
        missing_members = required_members - existing_members

        if missing_members:
            LOGGER.info("adding members {} to team {}".format(
                ", ".join(missing_members), team.name))
        else:
            LOGGER.info("{} already in team {}, skipping team...".format(
                ", ".join(required_members), team.name))

        for username in missing_members:
            self._add_to_team(username, team)

    def _add_to_team(self, username: str, team: _Team):
        """Add a user with the given username to a team.

        Args:
            username: A username.
            team: A _Team.
        """
        try:
            member = self._api.get_user(username)
        except github.GithubException as exc:
            if exc.status != 404:
                raise GitHubError(
                    "Got unexpected response code from the GitHub API",
                    status=exc.status)
            LOGGER.warning("user {} does not exist, skipping".format(username))

        self._api.add_to_team(member, team)

    def create_repos(self, repo_infos: Iterable[RepoInfo]):
        """Create repositories in the given organization according to the RepoInfos.
        Repos that already exist are skipped.

        Args:
            repo_infos: An iterable of RepoInfo namedtuples.

        Returns:
            A list of urls to all repos corresponding to the RepoInfos.
        """
        repo_urls = []
        for info in repo_infos:
            try:
                print(info)
                repo_urls.append(self._api.create_repo(info))
                LOGGER.info("created {}/{}".format(self._api.org_name,
                                                   info.name))
            except GitHubError as exc:
                if exc.status != 422:
                    raise UnexpectedException(
                        "Got unexpected response code {} from the GitHub API".
                        format(exc.status))
                LOGGER.info("{}/{} already exists".format(
                    self._api.org_name, info.name))
                repo_urls.append(self._api.get_repo_url(info.name))
            except Exception as exc:
                raise UnexpectedException(
                    "An unexpected exception was raised.")
        return repo_urls
