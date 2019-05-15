"""GitHub API module.

This module contains the :py:class:`GitHubAPI` class, which is meant to be the
prime means of interacting with the GitHub API in ``repobee``. The methods of
GitHubAPI are mostly high-level bulk operations.

.. module:: github_api
    :synopsis: Top level interface for interacting with a GitHub instance
        within repobee.

.. moduleauthor:: Simon Larsén
"""
from typing import List, Iterable, Mapping, Optional, Generator, Tuple
from socket import gaierror
import collections
import daiquiri
import contextlib
import github
import gitlab

from repobee import exception
from repobee import tuples
from repobee import util

REQUIRED_OAUTH_SCOPES = {"admin:org", "repo"}

LOGGER = daiquiri.getLogger(__file__)

# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository

DEFAULT_REVIEW_ISSUE = tuples.Issue(
    title="Peer review",
    body="You have been assigned to peer review this repo.",
)


@contextlib.contextmanager
def _convert_404_to_not_found_error(msg):
    """Catch a github.GithubException with status 404 and convert to
    exception.NotFoundError with the provided message. If the GithubException
    does not have status 404, instead raise exception.UnexpectedException.
    """
    try:
        yield
    except github.GithubException as exc:
        if exc.status == 404:
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
        applicable if the exception is a github.GithubException).

    Raises:
        exception.NotFoundError
        exception.BadCredentials
        exception.GitHubError
        exception.ServiceNotFoundError
        exception.UnexpectedException
    """
    try:
        yield
    except gitlab.exceptions.GitlabCreateError:
        pass
    except github.GithubException as e:
        if ignore_statuses and e.status in ignore_statuses:
            return

        if e.status == 404:
            raise exception.NotFoundError(str(e), status=404)
        elif e.status == 401:
            raise exception.BadCredentials(
                "credentials rejected, verify that token has correct access.",
                status=401,
            )
        else:
            raise exception.GitHubError(str(e), status=e.status)
    except gaierror:
        raise exception.ServiceNotFoundError(
            "GitHub service could not be found, check the url"
        )
    except Exception as e:
        raise exception.UnexpectedException(
            "a {} occured unexpectedly: {}".format(type(e).__name__, str(e))
        )


class GitLabAPI:
    User = collections.namedtuple("User", ("id", "login"))

    def __init__(self, base_url, token, org_name, user: str = None):
        if user:
            LOGGER.warning("user is ignored when using GitLab")
        self._user = "oauth2"
        self._gitlab = gitlab.Gitlab(base_url, private_token=token)
        self._group_name = org_name
        self._group = self.get_organization(self._group_name)
        self._token = token
        self._base_url = base_url

    @property
    def org(self):
        return self._group

    def get_teams_in(
        self, team_names: Iterable[str]
    ) -> Generator[github.Team.Team, None, None]:
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

    def delete_teams(self, team_names: Iterable[str]) -> None:
        """Delete all teams that match any of the team names. Skip any team
        name for which no team can be found.

        Args:
            team_names: A list of team names for teams to be deleted.
        """
        raise NotImplementedError()
        deleted = set()  # only for logging
        for team in self.get_teams_in(team_names):
            team.delete()
            deleted.add(team.name)
            LOGGER.info("deleted team {}".format(team.name))

        # only logging
        missing = set(team_names) - deleted
        if missing:
            LOGGER.warning(
                "could not find teams: {}".format(", ".join(missing))
            )

    def ensure_teams_and_members(
        self,
        member_lists: Mapping[str, Iterable[str]],
        permission: str = "push",
    ) -> List[tuples.Team]:
        """Create teams that do not exist and add members not in their
        specified teams (if they exist as users).

        Args:
            member_list: A mapping of (team_name, member_list).

        Returns:
            A list of Team namedtuples of the teams corresponding to the keys
            of the member_lists mapping.
        """
        teams = self.ensure_teams_exist(
            [str(team_name) for team_name in member_lists.keys()],
            permission=permission,
        )

        for team in [team for team in teams if member_lists[team.name]]:
            self._ensure_members_in_team(team, member_lists[team.name])

        return list(self.get_teams_in(set(member_lists.keys())))

    def _ensure_members_in_team(
        self, team: github.Team.Team, members: Iterable[str]
    ):
        """Add all of the users in ``members`` to a team. Skips any users that
        don't exist, or are already in the team.

        Args:
            team: A _Team object to which members should be added.
            members: An iterable of usernames.
        """
        existing_members = set(
            member.login for member in self.get_members(team)
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
        self.add_to_team(missing_members, team)

    def get_organization(self, org_name):
        return [
            g
            for g in self._gitlab.groups.list(search=org_name)
            if g.name == org_name
        ][0]

    def get_members(self, group):
        return [self.User(m.id, m.username) for m in group.members.list()]

    def get_teams(self):
        return self._gitlab.groups.list(id=self._group.id)

    def add_to_team(self, members: Iterable[str], team: github.Team.Team):
        """Add members to a team.

        Args:
            members: Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            users = self.get_users(members)
            for user in users:
                team.members.create(
                    {
                        "user_id": user.id,
                        "access_level": gitlab.DEVELOPER_ACCESS,
                    }
                )

    def get_users(self, usernames):
        users = []
        for name in usernames:
            user = self._gitlab.users.list(username=name)
            if not user:
                LOGGER.warning("user {} could not be found".format(users))
            users += user
        return users

    def ensure_teams_exist(
        self, team_names: Iterable[str], permission: str = "push"
    ) -> List[tuples.Team]:
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
            created = False
            with _try_api_request(ignore_statuses=[400]):
                repo_urls.append(
                    self._gitlab.projects.create(
                        {
                            "name": info.name,
                            "path": info.name,
                            "description": info.description,
                            "visibility": "private"
                            if info.private
                            else "public",
                            "namespace_id": info.team_id,
                        }
                    ).attributes["http_url_to_repo"]
                )
                LOGGER.info(
                    "created {}/{}".format(self._group.name, info.name)
                )
                created = True

            if not created:
                # TODO optimize, this team get is redundant
                team_name = self._gitlab.groups.get(info.team_id).path
                repo_urls.append(
                    self._gitlab.projects.get(
                        "/".join([self._group.path, team_name, info.name])
                    ).attributes["http_url_to_repo"]
                )
                LOGGER.info(
                    "{}/{} already exists".format(self._group.name, info.name)
                )

        return [self._insert_auth(url) for url in repo_urls]

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        students: Optional[List[tuples.Group]] = None,
    ) -> List[str]:
        """Get repo urls for all specified repo names in organization. Assumes
        that the repos exist, there is no guarantee that they actually do as
        checking this with the REST API takes too much time.

        If the `students` argument is supplied, student repo urls are
        computed instead of master repo urls.

        Args:
            master_repo_names: A list of master repository names.
            org_name: Organization in which repos are expected. Defaults to the
                target organization of the API instance.
            students: A list of student groups.

        Returns:
            a list of urls corresponding to the repo names.
        """
        group_url = f"{self._base_url}/{self._group_name}"
        repo_urls = (
            [
                "{}/{}.git".format(group_url, repo_name)
                for repo_name in master_repo_names
            ]
            if not students
            else [
                "{}/{}/{}.git".format(
                    group_url,
                    student,
                    util.generate_repo_name(str(student), master_repo_name),
                )
                for student in students
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
        # TODO remove http hack
        if not repo_url.startswith("https://"):
            raise ValueError(
                "unsupported protocol in '{}', please use https:// ".format(
                    repo_url
                )
            )
        auth = "{}:{}".format(self._user, self._token)
        return repo_url.replace("https://", "https://{}@".format(auth))

    def get_issues(
        self,
        repo_names: Iterable[str],
        state: str = "open",
        title_regex: str = "",
    ):
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
        raise NotImplementedError()

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        """Open the specified issue in all repos with the given names.

        Args:
            title: Title of the issue.
            body: Body of the issue.
            repo_names: Names of repos to open the issue in.
        """
        raise NotImplementedError()

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """Close any issues in the given repos whose titles match the title_regex.

        Args:
            title_regex: A regex to match against issue titles.
            repo_names: Names of repositories to close issues in.
        """
        raise NotImplementedError()

    def add_repos_to_review_teams(
        self,
        team_to_repos: Mapping[str, Iterable[str]],
        issue: Optional[tuples.Issue],
    ) -> None:
        """Add repos to review teams. For each repo, an issue is opened, and
        every user in the review team is assigned to it. If no issue is
        specified, sensible defaults for title and body are used.

        Args:
            team_to_repos: A mapping from a team name to a sequence of repo
                names.
            issue: An an optional Issue tuple to override the default issue.
        """
        raise NotImplementedError()

    def get_review_progress(
        self, review_team_names, students, title_regex
    ) -> Mapping[str, List[tuples.Review]]:
        """Get the peer review progress for the specified review teams and
        students. Only issues matching the title regex will be considered peer
        review issues. If a reviewer has opened an issue in the assigned repo
        with a title matching the regex, the review will be considered done.

        Note that reviews only count if the student is in the review team for
        that repo. Review teams must only have one associated repo, or the
        repo is skipped. This could potentially be relaxed if there is reason
        to, because it is not critical to the functionality of the algorithm.

        Args:
            review_team_names: Names of review teams.
            students: The reviewing students (supposedly also the ones being
                reviewed, but not necessarily)
            title_regex: If an issue title matches this regex, the issue is
                considered a potential peer review issue.
        Returns:
            a mapping (reviewer -> assigned_repos), where reviewer is a str and
            assigned_repos is a :py:class:`~repobee.tuples.Review`.
        """
        raise NotImplementedError()

    def add_repos_to_teams(
        self, team_to_repos: Mapping[str, Iterable[str]]
    ) -> Generator[
        Tuple[github.Team.Team, github.Repository.Repository], None, None
    ]:
        """Add repos to teams and yield each (team, repo) combination _after_
        the repo has been added to the team.

        Args:
            team_to_repos: A mapping from a team name to a sequence of repo
                names.
        Returns:
            a generator yielding each (team, repo) tuple in turn.
        """
        raise NotImplementedError()

    def _get_repos_by_name(
        self, repo_names: Iterable[str]
    ) -> Generator[_Repo, None, None]:
        """Get all repos that match any of the names in repo_names. Unmatched
        names are ignored (in both directions).

        Args:
            repo_names: Names of repos to fetch.

        Returns:
            a generator of repo objects.
        """
        raise NotImplementedError()

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ):
        """Verify the following:

        .. code-block: markdown

            1. Base url is correct (verify by fetching user).
            2. The token has correct access privileges (verify by getting oauth
               scopes)
            3. Organization exists (verify by getting the org)
                - If master_org_name is supplied, this is also checked to
                  exist.
            4. User is owner in organization (verify by getting
                - If master_org_name is supplied, user is also checked to be an
                  owner of it.
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
        raise NotImplementedError()
