"""GitHub API module.

This module contains the :py:class:`GitHubAPI` class, which is meant to be the
prime means of interacting with the GitHub API in ``repomate``. The methods of
GitHubAPI are mostly high-level bulk operations.

The :py:class:`APIWrapper` class is an abstraction layer for the actual API
used to communicate with GitHub.

.. module:: github_api
    :synopsis: Top level interface for interacting with a GitHub instance within repomate.

.. moduleauthor:: Simon Larsén
"""
from typing import List, Iterable, Mapping
import daiquiri

from repomate import APIWrapper
from repomate import exception
from repomate import tuples

LOGGER = daiquiri.getLogger(__file__)


class GitHubAPI:
    """A highly specialized GitHub API class for repomate. The API is
    affiliated both with an organization, and with the whole GitHub
    instance. Almost all operations take place on the target
    organization.
    """

    def __init__(self, base_url: str, token: str, org_name: str):
        """Set up the GitHub API object.

        Args:
            base_url: The base url to a GitHub REST api (e.g.
            https://api.github.com for GitHub or https://<HOST>/api/v3 for
            Enterprise).
            token: A GitHub OAUTH token.
            org_name: Name of the target organization.
        """
        self._api = APIWrapper(base_url, token, org_name)
        self._org_name = org_name
        self._base_url = base_url
        self._token = token

    def __repr__(self):
        return "GitHubAPI(base_url={}, token={}, org_name={})".format(
            self._base_url, self._token, self._org_name)

    def ensure_teams_and_members(
            self,
            member_lists: Mapping[str, Iterable[str]]) -> List[tuples.Team]:
        """Create teams that do not exist and add members not in their
        specified teams (if they exist as users).

        Args:
            member_list: A mapping of (team_name, member_list).

        Returns:
            A list of Team namedtuples of the teams corresponding to the keys of
            the member_lists mapping.
        """
        teams = self._ensure_teams_exist(
            [team_name for team_name in member_lists.keys()])

        for team in [team for team in teams if member_lists[team.name]]:
            self._ensure_members_in_team(team, member_lists[team.name])

        return self._api.get_teams_in(set(member_lists.keys()))

    def _ensure_teams_exist(self,
                            team_names: Iterable[str]) -> List[tuples.Team]:
        """Create any teams that do not yet exist.
        
        Args:
            team_names: An iterable of team names.
        Returns:
            A list of Team namedtuples representing the teams corresponding to the
            provided team_names.
        Raises:
            exception.UnexpectedException if anything but a 422 (team already
            exists) is raised when trying to create a team.
        """
        existing_team_names = set(team.name for team in self._api.get_teams())

        required_team_names = set(team_names)
        for team_name in required_team_names - existing_team_names:
            try:
                self._api.create_team(team_name, permission='push')
                LOGGER.info("created team {}".format(team_name))
            except exception.GitHubError as exc:
                if exc.status != 422:
                    raise exception.UnexpectedException(
                        "Unexpected GitHubError {} on team creation: {}".
                        format(exc.status, str(exc)))
                LOGGER.info("team {} already exists".format(team_name))

        teams = [
            team for team in self._api.get_teams()
            if team.name in required_team_names
        ]
        return teams

    def _ensure_members_in_team(self, team: tuples.Team,
                                members: Iterable[str]):
        """Add all of the users in ``members`` to a team. Skips any users that
        don't exist, or are already in the team.

        Args:
            team: A _Team object to which members should be added.
            members: An iterable of usernames.
        """
        existing_members = set(team.members)
        missing_members = [
            member for member in members if member not in existing_members
        ]

        if missing_members:
            LOGGER.info("adding members {} to team {}".format(
                ", ".join(missing_members), team.name))
        if existing_members:
            LOGGER.info("{} already in team {}, skipping...".format(
                ", ".join(members), team.name))
        self._api.add_to_team(missing_members, team)

    def create_repos(self, repo_infos: Iterable[tuples.Repo]):
        """Create repositories in the given organization according to the Repos.
        Repos that already exist are skipped.

        Args:
            repo_infos: An iterable of Repo namedtuples.

        Returns:
            A list of urls to all repos corresponding to the Repos.
        """
        repo_urls = []
        for info in repo_infos:
            try:
                repo_urls.append(self._api.create_repo(info))
                LOGGER.info("created {}/{}".format(self._org_name, info.name))
            except exception.GitHubError as exc:
                if exc.status != 422:
                    raise exception.UnexpectedException(
                        "Got unexpected response code {} from the GitHub API".
                        format(exc.status))
                LOGGER.info("{}/{} already exists".format(
                    self._org_name, info.name))
                repo_urls.append(self._api.get_repo_url(info.name))
            except Exception as exc:
                raise exception.UnexpectedException(
                    "An unexpected exception was raised.")
        return repo_urls

    def get_repo_urls(self, repo_names: Iterable[str]) -> List[str]:
        """Get repo urls for all specified repo names in the current organization.
        Assumes that the repos exist, there is no guarantee that they actually do
        as checking this with the REST API takes too much time.

        Args:
            repo_names: A list of repository names.

        Returns:
            a list of urls corresponding to the repo names.
        """
        return [
            "{}/{}".format(self._api.org_url, repo_name)
            for repo_name in list(repo_names)
        ]

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
        yield from self._api.get_issues(repo_names, state, title_regex)

    def open_issue(self, issue: tuples.Issue,
                   repo_names: Iterable[str]) -> None:
        """Open the specified issue in all repos with the given names.

        Args:
            issue: The issue to open.
            repo_names: Names of repos to open the issue in.
        """
        self._api.open_issue_in(issue, repo_names)

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """Close any issues in the given repos whose titles match the title_regex.

        Args:
            title_regex: A regex to match against issue titles.
            repo_names: Names of repositories to close issues in.
        """
        self._api.close_issue_in(title_regex, repo_names)
