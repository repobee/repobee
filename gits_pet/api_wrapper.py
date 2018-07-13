"""Wrapper module for the GitHub API.

This module wraps PyGithub's main class and an organization in the ApiWrapper
class. The purpose of the module is to make it easy to swap out PyGithub at a
later date. There is some slight leakage of the PyGithub API in that the _Team,
_User and _Repo classes (aliases for PyGithub classes, see their definitions
below) are sometimes used externally. But really shouldn't.
"""
import contextlib
import collections
import re
from typing import Iterable, Mapping, Optional, List, Generator
import daiquiri
import github

from gits_pet import exception

LOGGER = daiquiri.getLogger(__file__)

# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository

# classes also used externally
Team = collections.namedtuple('Team', ('name', 'members', 'id'))
RepoInfo = collections.namedtuple(
    'RepoInfo', ('name', 'description', 'private', 'team_id'))


@contextlib.contextmanager
def _try_api_request():
    """Context manager for trying API requests."""
    try:
        yield
    except github.GithubException as e:
        if e.status == 404:
            raise exception.NotFoundError(str(e), status=404)
        else:
            raise exception.GitHubError(str(e), status=e.status)
    except Exception as e:
        raise exception.UnexpectedException(
            "An unexpected exception occured. This is "
            "probably a bug, please report it.")


class ApiWrapper:
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

    def get_teams_in(self, team_names: Iterable[str]) -> Iterable[Team]:
        """Get all teams that match any team name in the team_names iterable.

        Args:
            team_names: An iterable of team names.

        Returns:
            An iterable of Team namedtuples of all teams that matched any of the team names.
        """
        team_names = set(team_names)
        with _try_api_request():
            return [
                Team(
                    name=team.name,
                    members=[m.name for m in team.get_members()],
                    id=team.id) for team in self.get_teams()
                if team.name in team_names
            ]

    def add_to_team(self, member: _User, team: _Team):
        """Add a user to a team.

        Args:
            member: A user to add to the team.
            team: A _Team.
        """
        with _try_api_request():
            team.add_membership(member)

    def get_repo_url(self, repo_name: str) -> str:
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
            return self._org.create_team(team_name, permission=permission)

    def get_repos(self,
                  regex: Optional[str] = None) -> Generator[_Repo, None, None]:
        """Get repo objects for all repositories in the organization. If a
        regex is supplied, only return urls to repos whos names match the

        Args:
            regex: An optional regex for filtering repos based on name.

        Returns:
            a generator of repo objects.
        """
        with _try_api_request():
            if regex:
                yield from (repo for repo in self._org.get_repos()
                            if re.match(regex, repo.name))
            else:
                yield from self._org.get_repos()

    def get_repos_by_name(
            self, repo_names: Iterable[str]) -> Generator[_Repo, None, None]:
        """Get all repos that match any of the names in repo_names. Unmatched
        names are ignored (in both directions).

        Args:
            repo_names: Names of repos to fetch.

        Returns:
            a generator of repo objects.
        """
        name_set = set(repo_names)
        with _try_api_request():
            return (repo for repo in self._org.get_repos()
                    if repo.name in name_set)
