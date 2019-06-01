"""GitLab API module.

This module contains the :py:class:`GitLabAPI` class, which is meant to be the
prime means of interacting with the GitLab API in RepoBee. The methods of
GitLabAPI are mostly high-level bulk operations.

.. module:: gitlab_api
    :synopsis: Top level interface for interacting with a GitLab instance
        within repobee.

.. moduleauthor:: Simon Larsén
"""
from typing import List, Iterable, Optional
from socket import gaierror
import collections
import contextlib

import daiquiri
import gitlab

from repobee import exception
from repobee import apimeta
from repobee import util

LOGGER = daiquiri.getLogger(__file__)


@contextlib.contextmanager
def _convert_404_to_not_found_error(msg):
    try:
        yield
    except gitlab.exceptions.GitlabError as exc:
        if exc.response_code == 404:
            raise exception.NotFoundError(msg)
        raise exception.UnexpectedException(
            "An unexpected exception occured. {.__name__}: {}".format(
                type(exc), str(exc)
            )
        )


@contextlib.contextmanager
def _try_api_request(ignore_statuses: Optional[Iterable[int]] = None):
    """Context manager for trying API requests.

    Args:
        ignore_statuses: One or more status codes to ignore (only
        applicable if the exception is a gitlab.exceptions.GitlabError).
    """
    try:
        yield
    except gitlab.exceptions.GitlabError as e:
        if ignore_statuses and e.response_code in ignore_statuses:
            return

        if e.response_code == 404:
            raise exception.NotFoundError(str(e), status=404)
        elif e.response_code == 401:
            raise exception.BadCredentials(
                "credentials rejected, verify that token has correct access.",
                status=401,
            )
        else:
            raise exception.APIError(str(e), status=e.response_code)
    except gaierror:
        raise exception.ServiceNotFoundError(
            "GitLab service could not be found, check the url"
        )
    except Exception as e:
        raise exception.UnexpectedException(
            "a {} occured unexpectedly: {}".format(type(e).__name__, str(e))
        )


class GitLabAPI(apimeta.API):
    _User = collections.namedtuple("_User", ("id", "login"))

    def __init__(self, base_url, token, org_name, user: str = None):
        if user:
            LOGGER.warning("user is ignored when using GitLab")
        self._user = "oauth2"
        self._gitlab = gitlab.Gitlab(base_url, private_token=token)
        self._group_name = org_name
        self._group = self._get_organization(self._group_name)
        self._token = token
        self._base_url = base_url

    def _get_teams_in(self, team_names: Iterable[str]):
        """Get all teams that match any team name in the team_names iterable.

        Args:
            team_names: An iterable of team names.
        Returns:
            An iterable of Team namedtuples of all teams that matched any of
            the team names.
        """
        team_names = set(team_names)
        with _try_api_request():
            return (
                team for team in self.get_teams() if team.name in team_names
            )

    def ensure_teams_and_members(
        self, teams: Iterable[apimeta.Team], permission: str = "push"
    ) -> List[apimeta.Team]:
        """See :py:func:`repobee.apimeta.APISpec.ensure_teams_and_members`."""
        member_lists = {team.name: team.members for team in teams}
        raw_teams = self._ensure_teams_exist(
            [str(team_name) for team_name in member_lists.keys()],
            permission=permission,
        )

        for team in [team for team in raw_teams if member_lists[team.name]]:
            self._ensure_members_in_team(team, member_lists[team.name])

        return [
            apimeta.Team(
                name=t.name,
                members=member_lists[t.name],
                id=t.id,
                implementation=t,
            )
            for t in raw_teams
        ]

    def _ensure_members_in_team(self, team, members: Iterable[str]):
        """Add all of the users in ``members`` to a team. Skips any users that
        don't exist, or are already in the team.
        """
        existing_members = set(
            member.login for member in self._get_members(team)
        )
        missing_members = [
            member for member in members if member not in existing_members
        ]

        if missing_members:
            LOGGER.info(
                "adding members {} to team {}".format(
                    ", ".join(missing_members), team.name
                )
            )
        if existing_members:
            LOGGER.info(
                "{} already in team {}, skipping...".format(
                    ", ".join(existing_members), team.name
                )
            )
        self._add_to_team(missing_members, team)

    def _get_organization(self, org_name):
        return [
            g
            for g in self._gitlab.groups.list(search=org_name)
            if g.name == org_name
        ][0]

    def _get_members(self, group):
        return [self._User(m.id, m.username) for m in group.members.list()]

    def get_teams(self) -> List[apimeta.Team]:
        """See :py:func:`repobee.apimeta.Team`."""
        return [
            apimeta.Team(
                name=t.name,
                members=[m.username for m in t.members.list()],
                id=t.id,
                implementation=t,
            )
            for t in self._gitlab.groups.list(id=self._group.id)
        ]

    def _add_to_team(self, members: Iterable[str], team):
        """Add members to a team.

        Args:
            members: _Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            users = self._get_users(members)
            for user in users:
                team.members.create(
                    {
                        "user_id": user.id,
                        "access_level": gitlab.DEVELOPER_ACCESS,
                    }
                )

    def _get_users(self, usernames):
        users = []
        for name in usernames:
            user = self._gitlab.users.list(username=name)
            # if not user:
            # LOGGER.warning("user {} could not be found".format(user))
            users += user
        return users

    def _ensure_teams_exist(
        self, team_names: Iterable[str], permission: str = "push"
    ) -> List[apimeta.Team]:
        """Create any teams that do not yet exist.

        Args:
            team_names: An iterable of team names.
        Returns:
            A list of Team namedtuples representing the teams corresponding to
            the provided team_names.
        Raises:
            exception.UnexpectedException if anything but a 422 (team already
            exists) is raised when trying to create a team.
        """
        existing_teams = list(self._gitlab.groups.list(id=self._group.id))
        existing_team_names = set(team.name for team in existing_teams)

        required_team_names = set(team_names)
        teams = [
            team for team in existing_teams if team.name in required_team_names
        ]

        parent_id = self._group.id
        for team_name in required_team_names - existing_team_names:
            with _try_api_request():
                new_team = self._gitlab.groups.create(
                    {
                        "name": team_name,
                        "path": team_name,
                        "parent_id": parent_id,
                    }
                )
                LOGGER.info("created team {}".format(team_name))
                teams.append(new_team)
        return teams

    def create_repos(self, repos: Iterable[apimeta.Repo]) -> List[str]:
        """See :py:func:`repobee.apimeta.APISpec.create_repos`."""
        repo_urls = []
        for repo in repos:
            created = False
            with _try_api_request(ignore_statuses=[400]):
                repo_urls.append(
                    self._gitlab.projects.create(
                        {
                            "name": repo.name,
                            "path": repo.name,
                            "description": repo.description,
                            "visibility": "private"
                            if repo.private
                            else "public",
                            "namespace_id": repo.team_id,
                        }
                    ).attributes["http_url_to_repo"]
                )
                LOGGER.info(
                    "created {}/{}".format(self._group.name, repo.name)
                )
                created = True

            if not created:
                # TODO optimize, this team get is redundant
                team_name = self._gitlab.groups.get(repo.team_id).path
                repo_urls.append(
                    self._gitlab.projects.get(
                        "/".join([self._group.path, team_name, repo.name])
                    ).attributes["http_url_to_repo"]
                )
                LOGGER.info(
                    "{}/{} already exists".format(self._group.name, repo.name)
                )

        return [self._insert_auth(url) for url in repo_urls]

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[apimeta.Team]] = None,
    ) -> List[str]:
        """See :py:func:`repobee.apimeta.APISpec.get_repo_urls`."""
        group_name = org_name if org_name else self._group_name
        group_url = "{}/{}".format(self._base_url, group_name)
        repo_urls = (
            [
                "{}/{}.git".format(group_url, repo_name)
                for repo_name in master_repo_names
            ]
            if not teams
            else [
                "{}/{}/{}.git".format(
                    group_url,
                    team,
                    util.generate_repo_name(str(team), master_repo_name),
                )
                for team in teams
                for master_repo_name in master_repo_names
            ]
        )
        return [self._insert_auth(url) for url in repo_urls]

    def _insert_auth(self, repo_url: str):
        """Insert an authentication token into the url.

        Args:
            repo_url: A HTTPS url to a repository.
        Returns:
            the input url with an authentication token inserted.
        """
        if not repo_url.startswith("https://"):
            raise ValueError(
                "unsupported protocol in '{}', please use https:// ".format(
                    repo_url
                )
            )
        auth = "{}:{}".format(self._user, self._token)
        return repo_url.replace("https://", "https://{}@".format(auth))
