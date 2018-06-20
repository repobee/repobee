"""GitHub API module.

This module contains the GitHubAPI class, which is meant to be the prime means
of interacting with the GitHub API in gits_pet. The methods of GitHubAPI are
mostly high-level bulk operations.
"""
import collections
from typing import List, Iterable, Mapping
import daiquiri
import github
from gits_pet.api_wrapper import (ApiWrapper, RepoInfo, GitHubError,
                                  UnexpectedException, Team, _Team, _User,
                                  _Repo)

LOGGER = daiquiri.getLogger(__file__)


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
        self._api = ApiWrapper(base_url, token, org_name)
        self._org_name = org_name
        self._base_url = base_url
        self._token = token

    def __repr__(self):
        return "GitHubAPI(base_url={}, token={}, org_name={})".format(
            self._base_url, self._token, self._org_name)

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

        return self._api.get_teams_in(set(member_lists.keys()))

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
            self._api.add_to_team(member, team)
        except GitHubError as exc:
            if exc.status != 404:
                raise GitHubError(
                    "Got unexpected response code from the GitHub API",
                    status=exc.status)
            LOGGER.warning("user {} does not exist, skipping".format(username))

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
                repo_urls.append(self._api.create_repo(info))
                LOGGER.info("created {}/{}".format(self._org_name,
                                                   info.name))
            except GitHubError as exc:
                if exc.status != 422:
                    raise UnexpectedException(
                        "Got unexpected response code {} from the GitHub API".
                        format(exc.status))
                LOGGER.info("{}/{} already exists".format(
                    self._org_name, info.name))
                repo_urls.append(self._api.get_repo_url(info.name))
            except Exception as exc:
                raise UnexpectedException(
                    "An unexpected exception was raised.")
        return repo_urls
