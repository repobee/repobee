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
import itertools
from typing import List, Iterable, Optional, Generator, Tuple, Mapping

import daiquiri
import gitlab
import requests.exceptions

import repobee_plug as plug

from _repobee import exception
from _repobee.ext.github import DEFAULT_REVIEW_ISSUE

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
    plug.TeamPermission.PULL: gitlab.REPORTER_ACCESS,
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
def _convert_error(expected, conversion, msg):
    try:
        yield
    except expected as exc:
        raise conversion(msg) from exc


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
            raise exception.NotFoundError(str(e), status=404) from e
        elif e.response_code == 401:
            raise exception.BadCredentials(
                "credentials rejected, verify that token has correct access.",
                status=401,
            ) from e
        else:
            raise exception.APIError(str(e), status=e.response_code) from e
    except Exception as e:
        raise exception.UnexpectedException(
            "a {} occured unexpectedly: {}".format(type(e).__name__, str(e))
        ) from e


class GitLabAPI(plug.API):
    _User = collections.namedtuple("_User", ("id", "login"))

    def __init__(self, base_url, token, org_name):
        # ssl turns off only for
        self._user = "oauth2"
        self._gitlab = gitlab.Gitlab(
            base_url, private_token=token, ssl_verify=self._ssl_verify()
        )
        self._group_name = org_name
        self._token = token
        self._base_url = base_url

        with _try_api_request():
            self._gitlab.auth()
            self._actual_user = self._gitlab.user.username
            self._group = self._get_organization(self._group_name)

    @staticmethod
    def _ssl_verify():
        ssl_verify = not os.getenv("REPOBEE_NO_VERIFY_SSL") == "true"
        if not ssl_verify:
            LOGGER.warning("SSL verification turned off, only for testing")
        return ssl_verify

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
        with _try_api_request():
            member_lists = {team.name: team.members for team in teams}
            raw_permission = _TEAM_PERMISSION_MAPPING[permission]
            raw_teams = self._ensure_teams_exist(
                [str(team_name) for team_name in member_lists.keys()],
                permission=raw_permission,
            )

            for team in [
                team for team in raw_teams if member_lists[team.name]
            ]:
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
        with _try_api_request():
            teams = [
                plug.Team(
                    name=t.name,
                    members=[m.username for m in t.members.list()],
                    id=t.id,
                    implementation=t,
                )
                for t in self._gitlab.groups.list(id=self._group.id)
            ]
            return teams

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
                with _try_api_request():
                    # TODO optimize, this team get is redundant
                    team_name = self._gitlab.groups.get(repo.team_id).path
                    repo_urls.append(
                        self._gitlab.projects.get(
                            "/".join([self._group.path, team_name, repo.name])
                        ).attributes["http_url_to_repo"]
                    )
                    LOGGER.info(
                        "{}/{} already exists".format(
                            self._group.name, repo.name
                        )
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
                    plug.generate_repo_name(str(team), master_repo_name),
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

    def _get_projects_and_names_by_name(self, repo_names, strict=False):
        """Return lazy projects (minimal amount of info loaded) along with
        their names.

        If strict is True, raise an exception if any of the repos are not
        found.
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
            msg = "Can't find repos: {}".format(", ".join(missing))
            if strict:
                raise exception.NotFoundError(msg)
            LOGGER.warning(msg)

    def delete_teams(self, team_names: Iterable[str]) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.delete_teams`."""
        deleted = set()  # only for logging
        team_names = set(team_names)
        for team in self._get_teams_in(team_names):
            team.implementation.delete()
            deleted.add(team.name)
            LOGGER.info("Deleted team {}".format(team.name))

        # only logging
        missing = set(team_names) - deleted
        if missing:
            LOGGER.warning(
                "Could not find teams: {}".format(", ".join(missing))
            )

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.open_issue`."""
        with _try_api_request():
            projects = self._get_projects_and_names_by_name(repo_names)
            for lazy_project, project_name in projects:
                self._create_issue(
                    lazy_project,
                    dict(title=title, description=body),
                    project_name,
                )

    @staticmethod
    def _create_issue(project, issue_dict, project_name=None):
        project_name = project_name or project.name
        issue = project.issues.create(issue_dict)
        LOGGER.info(
            "Opened issue {}/#{}-'{}'".format(
                project_name, issue.id, issue.title
            )
        )

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.close_issue`."""
        closed = 0
        with _try_api_request():
            projects = self._get_projects_and_names_by_name(repo_names)
            issues_and_project_names = (
                (issue, project_name)
                for project, project_name in projects
                for issue in project.issues.list(state="opened")
                if re.match(title_regex, issue.title)
            )
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
        with _try_api_request():
            projects = self._get_projects_and_names_by_name(repo_names)
            raw_state = _ISSUE_STATE_MAPPING[state]
            name_issues_pairs = (
                (
                    project_name,
                    (
                        plug.Issue(
                            title=issue.title,
                            body=issue.description,
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

    def add_repos_to_review_teams(
        self,
        team_to_repos: Mapping[str, Iterable[str]],
        issue: Optional[plug.Issue] = None,
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.add_repos_to_review_teams`.
        """
        issue = issue or DEFAULT_REVIEW_ISSUE
        raw_teams = [
            team.implementation
            for team in self._get_teams_in(team_to_repos.keys())
        ]
        project_names = set(
            itertools.chain.from_iterable(team_to_repos.values())
        )
        projects = {
            name: project
            for project, name in self._get_projects_and_names_by_name(
                project_names, strict=True
            )
        }
        for team in raw_teams:
            member_ids = [
                member.id
                for member in team.members.list()
                if member.username != self._actual_user
            ]
            for proj_name in team_to_repos[team.name]:
                lazy_project = projects[proj_name]
                with _try_api_request(ignore_statuses=[409]):
                    # 409 if project is already shared
                    lazy_project.share(
                        team.id,
                        group_access=_TEAM_PERMISSION_MAPPING[
                            plug.TeamPermission.PULL
                        ],
                    )
                self._create_issue(
                    lazy_project,
                    dict(
                        title=issue.title,
                        description=issue.body,
                        assignee_ids=member_ids,
                    ),
                    proj_name,
                )

    def get_review_progress(
        self,
        review_team_names: Iterable[str],
        teams: Iterable[plug.Team],
        title_regex: str,
    ) -> Mapping[str, List[plug.Review]]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_review_progress`."""
        reviews = collections.defaultdict(list)
        raw_review_teams = [
            team.implementation
            for team in self._get_teams_in(review_team_names)
        ]
        for raw_team in raw_review_teams:
            with _try_api_request():
                LOGGER.info("Processing {}".format(raw_team.name))
                reviewers = set(m.username for m in raw_team.members.list())
                review_teams = self._extract_review_teams(teams, reviewers)
                projects = raw_team.projects.list()
                if len(projects) != 1:
                    LOGGER.warning(
                        "Expected {} to have 1 associated projects, found {}."
                        "Skipping...".format(raw_team.name, len(projects))
                    )
                    continue

                proj = self._gitlab.projects.get(projects[0].id)
                review_issue_authors = {
                    issue.author["username"]
                    for issue in proj.issues.list()
                    if re.match(title_regex, issue.title)
                }

                for team in review_teams:
                    reviews[str(team)].append(
                        plug.Review(
                            repo=proj.path,
                            done=any(
                                map(
                                    review_issue_authors.__contains__,
                                    team.members,
                                )
                            ),
                        )
                    )
        return reviews

    def _extract_review_teams(self, teams, reviewers):
        review_teams = []
        for team in teams:
            if any(map(team.members.__contains__, reviewers)):
                review_teams.append(team)
        return review_teams

    def discover_repos(
        self, teams: Iterable[plug.Team]
    ) -> Generator[plug.Repo, None, None]:
        """See :py:meth:`repobee_plug.APISpec.discover_repos`."""
        # TODO optimizi by using team.implementation, if available
        with _try_api_request():
            team_names = [team.name for team in teams]
            groups = [
                team.implementation for team in self._get_teams_in(team_names)
            ]
            for group in groups:
                group_projects = group.projects.list(include_subgroups=True)
                for group_project in group_projects:
                    project = self._gitlab.projects.get(group_project.id)
                    yield plug.Repo(
                        name=project.name,
                        description=project.description,
                        private=project.visibility == "private",
                        team_id=group.id,
                        url=self._insert_auth(project.http_url_to_repo),
                        implementation=project,
                    )
        yield from []  # in case there are no matches

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ):
        """See :py:meth:`repobee_plug.apimeta.APISpec.verify_settings`."""
        LOGGER.info("GitLabAPI is verifying settings ...")
        if not token:
            raise exception.BadCredentials(
                msg="Token is empty. Check that REPOBEE_TOKEN environment "
                "variable is properly set, or supply the `--token` option."
            )

        gl = gitlab.Gitlab(
            base_url, private_token=token, ssl_verify=GitLabAPI._ssl_verify()
        )

        LOGGER.info("Authenticating connection to {}...".format(base_url))
        with _convert_error(
            gitlab.exceptions.GitlabAuthenticationError,
            exception.BadCredentials,
            "Could not authenticate token",
        ), _convert_error(
            requests.exceptions.ConnectionError,
            exception.APIError,
            "Could not connect to {}, please check the URL".format(base_url),
        ):
            gl.auth()
        LOGGER.info(
            "SUCCESS: Authenticated as {} at {}".format(
                gl.user.username, base_url
            )
        )

        GitLabAPI._verify_group(org_name, gl)
        if master_org_name:
            GitLabAPI._verify_group(master_org_name, gl)

        LOGGER.info("GREAT SUCCESS: All settings check out!")

    @staticmethod
    def _verify_group(group_name: str, gl: gitlab.Gitlab) -> None:
        """Check that the group exists and that the user is an owner."""
        user = gl.user.username

        LOGGER.info("Trying to fetch group {}".format(group_name))
        slug_matched = [
            group
            for group in gl.groups.list(search=group_name)
            if group.path == group_name
        ]
        if not slug_matched:
            raise exception.NotFoundError(
                "Could not find group with slug {}. Verify that you have "
                "access to the group, and that you've provided the slug "
                "(the name in the address bar).".format(group_name)
            )
        group = slug_matched[0]
        LOGGER.info("SUCCESS: Found group {}".format(group.name))

        LOGGER.info(
            "Verifying that user {} is an owner of group {}".format(
                user, group_name
            )
        )
        matching_members = [
            member
            for member in group.members.list()
            if member.username == user
            and member.access_level == gitlab.OWNER_ACCESS
        ]
        if not matching_members:
            raise exception.BadCredentials(
                "User {} is not an owner of {}".format(user, group_name)
            )
        LOGGER.info(
            "SUCCESS: User {} is an owner of group {}".format(user, group_name)
        )


class GitLabAPIHook(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "token", "org_name")

    def get_api_class(self):
        return GitLabAPI
