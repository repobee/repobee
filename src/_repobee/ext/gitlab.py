"""GitLab API module.

This module contains the :py:class:`GitLabAPI` class, which is meant to be the
prime means of interacting with the GitLab API in RepoBee. The methods of
GitLabAPI are mostly high-level bulk operations.

.. module:: gitlab
    :synopsis: Top level interface for interacting with a GitLab instance
        within _repobee.

.. moduleauthor:: Simon Larsén
"""
import os
import re
import collections
import contextlib
import pathlib
from typing import List, Iterable, Optional, Generator, Tuple
from socket import gaierror

import daiquiri
import gitlab

import repobee_plug as plug

from _repobee import exception
from _repobee import util

LOGGER = daiquiri.getLogger(__file__)


ISSUE_GENERATOR = Generator[plug.Issue, None, None]


# see https://docs.gitlab.com/ee/api/issues.html for mapping details
_ISSUE_STATE_MAPPING = {
    plug.IssueState.OPEN: "opened",
    plug.IssueState.CLOSED: "closed",
    plug.IssueState.ALL: "all",
}
# see https://docs.gitlab.com/ee/user/permissions.html for permission details
_TEAM_PERMISSION_MAPPING = {
    plug.TeamPermission.PULL: gitlab.GUEST_ACCESS,
    plug.TeamPermission.PUSH: gitlab.DEVELOPER_ACCESS,
}


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


class GitLabAPI(plug.API):
    _User = collections.namedtuple("_User", ("id", "login"))

    def __init__(self, base_url, token, org_name):
        # ssl turns off only for
        ssl_verify = not os.getenv("REPOBEE_NO_VERIFY_SSL") == "true"
        if not ssl_verify:
            LOGGER.warning("SSL verification turned off, only for testing")
        self._user = "oauth2"
        self._gitlab = gitlab.Gitlab(
            base_url, private_token=token, ssl_verify=ssl_verify
        )
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
        self,
        teams: Iterable[plug.Team],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> List[plug.Team]:
        """See
        :py:meth:`repobee_plug.apimeta.APISpec.ensure_teams_and_members`.
        """
        member_lists = {team.name: team.members for team in teams}
        raw_permission = _TEAM_PERMISSION_MAPPING[permission]
        raw_teams = self._ensure_teams_exist(
            [str(team_name) for team_name in member_lists.keys()],
            permission=raw_permission,
        )

        for team in [team for team in raw_teams if member_lists[team.name]]:
            self._ensure_members_in_team(
                team, member_lists[team.name], raw_permission
            )

        return [
            plug.Team(
                name=t.name,
                members=member_lists[t.name],
                id=t.id,
                implementation=t,
            )
            for t in raw_teams
        ]

    def _ensure_members_in_team(
        self, team, members: Iterable[str], permission: int
    ):
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
                "Adding members {} to team {}".format(
                    ", ".join(missing_members), team.name
                )
            )
        if existing_members:
            LOGGER.info(
                "{} already in team {}, skipping...".format(
                    ", ".join(existing_members), team.name
                )
            )
        self._add_to_team(missing_members, team, permission)

    def _get_organization(self, org_name):
        return [
            g
            for g in self._gitlab.groups.list(search=org_name)
            if g.path == org_name
        ][0]

    def _get_members(self, group):
        return [self._User(m.id, m.username) for m in group.members.list()]

    def get_teams(self) -> List[plug.Team]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_teams`."""
        return [
            plug.Team(
                name=t.name,
                members=[m.username for m in t.members.list()],
                id=t.id,
                implementation=t,
            )
            for t in self._gitlab.groups.list(id=self._group.id)
        ]

    def _add_to_team(self, members: Iterable[str], team, permission):
        """Add members to a team.

        Args:
            members: _Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            users = self._get_users(members)
            for user in users:
                team.members.create(
                    {"user_id": user.id, "access_level": permission}
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
        self, team_names: Iterable[str], permission
    ) -> List[plug.Team]:
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
                LOGGER.info("Created team {}".format(team_name))
                teams.append(new_team)
        return teams

    def create_repos(self, repos: Iterable[plug.Repo]) -> List[str]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.create_repos`."""
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
                            "namespace_id": repo.team_id
                            if repo.team_id
                            else self._group.id,
                        }
                    ).attributes["http_url_to_repo"]
                )
                LOGGER.info(
                    "Created {}/{}".format(self._group.name, repo.name)
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
        teams: Optional[List[plug.Team]] = None,
    ) -> List[str]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_repo_urls`."""
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

    def extract_repo_name(self, repo_url: str) -> str:
        """See :py:meth:`repobee_plug.apimeta.APISpec.extract_repo_name`."""
        return pathlib.Path(repo_url).stem

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

    def _get_projects_and_names_by_name(self, repo_names):
        """Return lazy projects (minimal amount of info loaded) along with
        their names.
        """
        projects = []
        for name in repo_names:
            candidates = self._group.projects.list(
                include_subgroups=True, search=name
            )
            for candidate in candidates:
                if candidate.name == name:
                    projects.append(candidate.name)
                    yield self._gitlab.projects.get(
                        candidate.id, lazy=True
                    ), candidate.name
                    break

        missing = set(repo_names) - set(projects)
        if missing:
            LOGGER.warning("Can't find repos: {}".format(", ".join(missing)))

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.open_issue`."""
        projects = self._get_projects_and_names_by_name(repo_names)
        for lazy_project, project_name in projects:
            issue = lazy_project.issues.create(dict(title=title, body=body))
            LOGGER.info(
                "Opened issue {}/#{}-'{}'".format(
                    project_name, issue.id, issue.title
                )
            )

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.close_issue`."""
        projects = self._get_projects_and_names_by_name(repo_names)
        issues_and_project_names = (
            (issue, project_name)
            for project, project_name in projects
            for issue in project.issues.list(state="opened")
            if re.match(title_regex, issue.title)
        )
        closed = 0
        for issue, project_name in issues_and_project_names:
            issue.state_event = "close"
            issue.save()
            LOGGER.info(
                "Closed issue {}/#{}-'{}'".format(
                    project_name, issue.id, issue.title
                )
            )
            closed += 1

        if closed:
            LOGGER.info("Closed {} issues".format(closed))
        else:
            LOGGER.warning("Found no issues matching the title regex")

    def get_issues(
        self,
        repo_names: Iterable[str],
        state: plug.IssueState = plug.IssueState.OPEN,
        title_regex: str = "",
    ) -> Generator[Tuple[str, ISSUE_GENERATOR], None, None]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_issues`."""
        projects = self._get_projects_and_names_by_name(repo_names)
        raw_state = _ISSUE_STATE_MAPPING[state]
        # TODO figure out how to get the issue body from the GitLab API...
        name_issues_pairs = (
            (
                project_name,
                (
                    plug.Issue(
                        title=issue.title,
                        body="<BODY UNAVAILABLE>",
                        number=issue.iid,
                        created_at=issue.created_at,
                        author=issue.author["username"],
                        implementation=issue,
                    )
                    for issue in project.issues.list(state=raw_state)
                    if re.match(title_regex, issue.title)
                ),
            )
            for project, project_name in projects
        )
        yield from name_issues_pairs


class GitLabAPIHook(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "token", "org_name")

    def get_api_class(self):
        return GitLabAPI
