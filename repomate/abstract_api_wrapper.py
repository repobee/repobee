"""Contains an abstract class defining an interface to a GitHub API.

Provides an abstract class that defines all of the functions required by the
:py:class:`repomate.github_api.GitHubAPI` class' internal API. The idea is to
completely separate :py:class:`repomate.github_api.GitHubAPI` from the API calls to the *actual*
GitHub API, so that the latter can be swapped out more easily. In theory,
any implementation of :py:class:`AbstractAPIWrapper` should be usable as the
API layer toward GitHub. The interface is however heavily influenced by the
fact that that it was created with regards to the REST v3 API, so utilizing
e.g. the GraphQL API efficiently may require some modification.

The currently used implementation of :py:class:`AbstractAPIWrapper` is defined
by the package level constant :py:const:`APIWrapper`.

Current implementations:

.. module:: abstract_api_wrapper
   :synopsis: Abstract class defining the interface required for the internal API of repomate.github_api.GitHubAPI.

.. moduleauthor:: Simon Larsén
"""

import abc

from typing import Optional, Iterable, Generator

from repomate import tuples

REQUIRED_OAUTH_SCOPES = {'admin:org', 'repo'}


class AbstractAPIWrapper(abc.ABC):
    """An abstract class that defines the internal API for
    :py:class:`repomate.github_api.GitHubAPI`. Methods should provide
    adequate logging where it makes sense.
    """

    @abc.abstractmethod
    def __init__(self, base_url: str, token: str, org_name: str):
        """
        Args:
            base_url: The base url to a GitHub REST api (e.g.
            https://api.github.com for GitHub or https://<HOST>/api/v3 for
            Enterprise).
            token: A GitHub OAUTH token.
            org_name: Name of an organization.
        """

    @abc.abstractmethod
    def get_teams(self) -> Iterable[tuples.Team]:
        """Returns: An iterable of the organization's teams."""

    @abc.abstractmethod
    def get_teams_in(self, team_names: Iterable[str]) -> Iterable[tuples.Team]:
        """Get all teams that match any team name in the team_names iterable.

        Args:
            team_names: An iterable of team names.
        Returns:
            An iterable of Team namedtuples of all teams that matched any of the team names.
        """

    @abc.abstractmethod
    def add_to_team(self, members: Iterable[str], team: tuples.Team):
        """Add members to a team.

        Args:
            member: Users to add to the team.
            team: A Team.
        """

    @abc.abstractmethod
    def open_issue_in(self, issue: tuples.Issue,
                      repo_names: Iterable[str]) -> None:
        """Open issues in all repos defined by repo_names, if they exist.
        Skip any repos that do not exist.

        Args:
            issue: The issue to open.
            repo_names: Names of repos in the target organization.
        """

    @abc.abstractmethod
    def close_issue_in(self, title_regex: str,
                       repo_names: Iterable[str]) -> None:
        """Close issues whose titles match the title_regex, in all repos
        defined by repo_names. Repos that do not exist are skipped.

        Args:
            title_regex: A regex to match against issue titles.
            repo_names: Names of repositories to close issues in.
        """

    @abc.abstractmethod
    def get_repo_url(self, repo_name: str) -> str:
        """Get a repo from the organization.
        
        Args:
            repo_name: Name of a repo.
        """

    @abc.abstractmethod
    def create_repo(self, repo_info: tuples.Repo):
        """Create a repo in the organization.

        Args:
            repo_info: Repo attributes.

        Returns:
            The html url to the repo.
        """

    @abc.abstractmethod
    def create_team(self, team_name: str, permission: str = 'push') -> None:
        """Create a team in the organization.

        Args:
            team_name: Name for the team.
            permission: The default access permission of the team.

        Returns:
            The created team.
        """

    @abc.abstractmethod
    def get_repos(self, repo_names: Optional[Iterable[str]]
                  ) -> Generator[tuples.Repo, None, None]:
        """Get repo objects for all repositories in the organization. If
        repo_names are supplied, fetches only repos that correspond with
        these names.

        Args:
            repo_names: An optional iterable of repo names.

        Returns:
            a generator of repo objects.
        """

    @abc.abstractmethod
    def get_issues(self,
                   repo_names: Iterable[str],
                   state: str = 'open',
                   title_regex: str = ""):
        """Get all issues for the repos in repo_names an return a generator
        that yields (repo_name, issue generator) tuples.

        Args:
            repo_names: An iterable of repo names.
            state: Specifying the state of the issue ('open' or 'closed').
            title_regex: If specified, only issues matching this regex are
            returned. Defaults to the empty string (which matches anything).
        Returns:
            A generator that yields (repo_name, issue generator) tuples.
        """

    @staticmethod
    @abc.abstractmethod
    def verify_settings(user: str, org_name: str, base_url: str, token: str):
        """Verify the following:

        .. code-block: markdown

            1. Base url is correct (verify by fetching user).
            2. The token has correct access privileges (verify by getting oauth scopes)
            3. Organization exists (verify by getting the org)
            4. User is owner in organization (verify by getting
            organization member list and checking roles)

            Raises exceptions if something goes wrong.

        Args:
            user: The username to try to fetch.
            org_name: Name of an organization.
            base_url: A base url to a github API.
            token: A secure OAUTH2 token.
        Returns:
            True if the connection is well formed.
        """
