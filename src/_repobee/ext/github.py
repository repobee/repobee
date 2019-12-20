"""GitHub API module.

This module contains the :py:class:`GitHubAPI` class, which is meant to be the
prime means of interacting with the GitHub API in ``repobee``. The methods of
GitHubAPI are mostly high-level bulk operations.

.. module:: github
    :synopsis: Top level interface for interacting with a GitHub instance
        within _repobee.

.. moduleauthor:: Simon Larsén
"""
import re
import pathlib
from typing import List, Iterable, Mapping, Optional, Generator, Tuple
from socket import gaierror
import collections
import contextlib

import daiquiri
import github

import repobee_plug as plug

from _repobee import exception

REQUIRED_TOKEN_SCOPES = {"admin:org", "repo"}
ISSUE_GENERATOR = Generator[plug.Issue, None, None]

LOGGER = daiquiri.getLogger(__file__)

_TEAM_PERMISSION_MAPPING = {
    plug.TeamPermission.PUSH: "push",
    plug.TeamPermission.PULL: "pull",
}
_ISSUE_STATE_MAPPING = {
    plug.IssueState.OPEN: "open",
    plug.IssueState.CLOSED: "closed",
    plug.IssueState.ALL: "all",
}


# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository

DEFAULT_REVIEW_ISSUE = plug.Issue(
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
        exception.APIError
        exception.ServiceNotFoundError
        exception.UnexpectedException
    """
    try:
        yield
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
            raise exception.APIError(str(e), status=e.status)
    except gaierror:
        raise exception.ServiceNotFoundError(
            "GitHub service could not be found, check the url"
        )
    except Exception as e:
        raise exception.UnexpectedException(
            "a {} occured unexpectedly: {}".format(type(e).__name__, str(e))
        )


class GitHubAPI(plug.API):
    """A highly specialized GitHub API class for _repobee. The API is
    affiliated both with an organization, and with the whole GitHub
    instance. Almost all operations take place on the target
    organization.
    """

    def __init__(self, base_url: str, token: str, org_name: str, user: str):
        """Set up the GitHub API object.

        Args:
            base_url: The base url to a GitHub REST api (e.g.
            https://api.github.com for GitHub or https://<HOST>/api/v3 for
            Enterprise).
            token: A GitHub access token.
            user: Name of the current user of the API.
            org_name: Name of the target organization.
        """
        if not user:
            raise TypeError("argument 'user' must not be empty")
        if not (
            base_url == "https://api.github.com"
            or base_url.endswith("/api/v3")
        ):
            raise plug.PlugError(
                "invalid base url, should either be https://api.github.com or "
                "end with '/api/v3'. See the docs: "
                "https://repobee.readthedocs.io/en/stable/"
                "getting_started.html#configure-repobee-for-the-target"
                "-organization-show-config-and-verify-settings"
            )
        self._github = github.Github(login_or_token=token, base_url=base_url)
        self._org_name = org_name
        self._base_url = base_url
        self._token = token
        self._user = user
        with _try_api_request():
            self._org = self._github.get_organization(self._org_name)

    def __repr__(self):
        return "GitHubAPI(base_url={}, token={}, org_name={})".format(
            self._base_url, self._token, self._org_name
        )

    @property
    def org(self):
        return self._org

    @property
    def token(self):
        return self._token

    def _get_teams_in(
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
            yield from (
                team
                for team in self.org.get_teams()
                if team.name in team_names
            )

    def get_teams(self) -> List[plug.Team]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_teams`."""
        return [
            plug.Team(
                name=t.name,
                members=[m.login for m in t.get_members()],
                id=t.id,
                implementation=t,
            )
            for t in self._org.get_teams()
        ]

    def delete_teams(self, team_names: Iterable[str]) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.delete_teams`."""
        deleted = set()  # only for logging
        for team in self._get_teams_in(team_names):
            team.delete()
            deleted.add(team.name)
            LOGGER.info("Deleted team {}".format(team.name))

        # only logging
        missing = set(team_names) - deleted
        if missing:
            LOGGER.warning(
                "Could not find teams: {}".format(", ".join(missing))
            )

    def _get_users(self, usernames: Iterable[str]) -> List[_User]:
        """Get all existing users corresponding to the usernames.
        Skip users that do not exist.

        Args:
            usernames: GitHub usernames.
        Returns:
            A list of _User objects.
        """
        existing_users = []
        for name in usernames:
            try:
                existing_users.append(self._github.get_user(name))
            except github.GithubException as exc:
                if exc.status != 404:
                    raise exception.APIError(
                        "Got unexpected response code from the GitHub API",
                        status=exc.status,
                    )
                LOGGER.warning("User {} does not exist".format(name))
        return existing_users

    def ensure_teams_and_members(
        self,
        teams: Iterable[plug.Team],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> List[plug.Team]:
        """See
        :py:meth:`repobee_plug.apimeta.APISpec.ensure_teams_and_members`.
        """
        raw_permission = _TEAM_PERMISSION_MAPPING[permission]
        member_lists = {team.name: team.members for team in teams}
        raw_teams = self._ensure_teams_exist(
            [team_name for team_name in member_lists.keys()],
            permission=raw_permission,
        )

        for team in [team for team in raw_teams if member_lists[team.name]]:
            self._ensure_members_in_team(team, member_lists[team.name])

        return [
            plug.Team(
                name=t.name,
                members=member_lists[t.name],
                id=t.id,
                implementation=t,
            )
            for t in raw_teams
        ]

    def _ensure_teams_exist(
        self, team_names: Iterable[str], permission: str = "push"
    ) -> List[github.Team.Team]:
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
        existing_teams = list(self._org.get_teams())
        existing_team_names = set(team.name for team in existing_teams)

        required_team_names = set(team_names)
        teams = [
            team for team in existing_teams if team.name in required_team_names
        ]

        for team_name in required_team_names - existing_team_names:
            with _try_api_request():
                new_team = self._org.create_team(
                    team_name, permission=permission
                )
                LOGGER.info("Created team {}".format(team_name))
                teams.append(new_team)
        return teams

    def _ensure_members_in_team(
        self, team: github.Team.Team, members: Iterable[str]
    ):
        """Add all of the users in ``members`` to a team. Skips any users that
        don't exist, or are already in the team.

        Args:
            team: A _Team object to which members should be added.
            members: An iterable of usernames.
        """
        existing_members = set(member.login for member in team.get_members())
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
        self._add_to_team(missing_members, team)

    def _add_to_team(self, members: Iterable[str], team: github.Team.Team):
        """Add members to a team.

        Args:
            members: Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            users = self._get_users(members)
            for user in users:
                team.add_membership(user)

    def create_repos(self, repos: Iterable[plug.Repo]):
        """See :py:meth:`repobee_plug.apimeta.APISpec.create_repos`."""
        repo_urls = []
        for info in repos:
            created = False
            with _try_api_request(ignore_statuses=[422]):
                kwargs = dict(
                    description=info.description, private=info.private
                )
                if info.team_id:  # using falsy results in an exception
                    kwargs["team_id"] = info.team_id
                repo_urls.append(
                    self._org.create_repo(info.name, **kwargs).html_url
                )
                LOGGER.info("Created {}/{}".format(self._org_name, info.name))
                created = True

            if not created:
                repo_urls.append(self._org.get_repo(info.name).html_url)
                LOGGER.info(
                    "{}/{} already exists".format(self._org_name, info.name)
                )

        return [self._insert_auth(url) for url in repo_urls]

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[plug.Team]] = None,
    ) -> List[str]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_repo_urls`."""
        with _try_api_request():
            org = (
                self._org
                if not org_name
                else self._github.get_organization(org_name)
            )
        repo_names = (
            master_repo_names
            if not teams
            else plug.generate_repo_names(teams, master_repo_names)
        )
        return [
            self._insert_auth(url)
            for url in (
                "{}/{}".format(org.html_url, repo_name)
                for repo_name in list(repo_names)
            )
        ]

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
        auth = "{}:{}".format(self._user, self.token)
        return repo_url.replace("https://", "https://{}@".format(auth))

    def get_issues(
        self,
        repo_names: Iterable[str],
        state: plug.IssueState = plug.IssueState.OPEN,
        title_regex: str = "",
    ) -> Generator[Tuple[str, ISSUE_GENERATOR], None, None]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_issues`."""
        repos = self._get_repos_by_name(repo_names)
        raw_state = _ISSUE_STATE_MAPPING[state]

        with _try_api_request():
            name_issues_pairs = (
                (
                    repo.name,
                    (
                        plug.Issue(
                            title=issue.title,
                            body=issue.body,
                            number=issue.number,
                            created_at=issue.created_at.isoformat(),
                            author=issue.user.login,
                            implementation=issue,
                        )
                        for issue in repo.get_issues(state=raw_state)
                        if re.match(title_regex or "", issue.title)
                    ),
                )
                for repo in repos
            )
        yield from name_issues_pairs

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.open_issue`."""
        repo_names_set = set(repo_names)
        repos = list(self._get_repos_by_name(repo_names_set))
        for repo in repos:
            with _try_api_request():
                created_issue = repo.create_issue(title, body=body)
            LOGGER.info(
                "Opened issue {}/#{}-'{}'".format(
                    repo.name, created_issue.number, created_issue.title
                )
            )

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.close_issue`."""
        repo_names_set = set(repo_names)
        repos = list(self._get_repos_by_name(repo_names_set))

        issue_repo_gen = (
            (issue, repo)
            for repo in repos
            for issue in repo.get_issues(state="open")
            if re.match(title_regex, issue.title)
        )
        closed = 0
        for issue, repo in issue_repo_gen:
            issue.edit(state="closed")
            LOGGER.info(
                "Closed issue {}/#{}-'{}'".format(
                    repo.name, issue.number, issue.title
                )
            )
            closed += 1

        if not closed:
            LOGGER.warning("Found no matching issues.")

    def add_repos_to_review_teams(
        self,
        team_to_repos: Mapping[str, Iterable[str]],
        issue: Optional[plug.Issue] = None,
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.add_repos_to_review_teams`.
        """
        issue = issue or DEFAULT_REVIEW_ISSUE
        for team, repo in self._add_repos_to_teams(team_to_repos):
            # TODO team.get_members() api request is a bit redundant, it
            # can be solved in a more efficient way by passing in the
            # allocations
            reviewers = team.get_members()
            created_issue = repo.create_issue(
                issue.title, body=issue.body, assignees=reviewers
            )
            LOGGER.info(
                "Opened issue {}/#{}-'{}'".format(
                    repo.name, created_issue.number, created_issue.title
                )
            )

    def get_review_progress(
        self,
        review_team_names: Iterable[str],
        teams: Iterable[plug.Team],
        title_regex: str,
    ) -> Mapping[str, List[plug.Review]]:
        """See :py:meth:`repobee_plug.apimeta.APISpec.get_review_progress`."""
        reviews = collections.defaultdict(list)
        review_team_impls = self._get_teams_in(review_team_names)
        for review_team_impl in review_team_impls:
            with _try_api_request():
                LOGGER.info("Processing {}".format(review_team_impl.name))
                reviewers = set(
                    m.login for m in review_team_impl.get_members()
                )
                review_teams = self._extract_review_teams(teams, reviewers)
                repos = list(review_team_impl.get_repos())
                if len(repos) != 1:
                    LOGGER.warning(
                        "Expected {} to have 1 associated repo, found {}."
                        "Skipping...".format(review_team_impl.name, len(repos))
                    )
                    continue

                repo = repos[0]
                review_issue_authors = {
                    issue.user.login
                    for issue in repo.get_issues()
                    if re.match(title_regex, issue.title)
                }

                for team in review_teams:
                    reviews[str(team)].append(
                        plug.Review(
                            repo=repo.name,
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

    def _add_repos_to_teams(
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
        team_names = set(team_to_repos.keys())
        with _try_api_request():
            teams = (
                team
                for team in self._org.get_teams()
                if team.name in team_names
            )
        for team in teams:
            repos = self._get_repos_by_name(team_to_repos[team.name])
            for repo in repos:
                LOGGER.info(
                    "Adding team {} to repo {} with '{}' permission".format(
                        team.name, repo.name, team.permission
                    )
                )
                with _try_api_request():
                    team.add_to_repos(repo)
                yield team, repo

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
        repos = set()
        for name in repo_names:
            with _try_api_request(ignore_statuses=[404]):
                repo = self._org.get_repo(name)
                yield repo
                repos.add(repo.name)

        missing_repos = set(repo_names) - repos
        if missing_repos:
            LOGGER.warning(
                "Can't find repos: {}".format(", ".join(missing_repos))
            )

    def discover_repos(
        self, teams: Iterable[plug.Team]
    ) -> Generator[plug.Repo, None, None]:
        """See :py:meth:`repobee_plug.APISpec.discover_repos`."""
        raw_teams = self._get_teams_in([team.name for team in teams])
        with _try_api_request():
            for team in raw_teams:
                for repo in team.get_repos():
                    yield plug.Repo(
                        name=repo.name,
                        description=repo.description,
                        private=repo.private,
                        team_id=team.id,
                        url=self._insert_auth(repo.html_url),
                        implementation=repo,
                    )

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ) -> None:
        """See :py:meth:`repobee_plug.apimeta.APISpec.verify_settings`."""
        LOGGER.info("Verifying settings ...")
        if not token:
            raise exception.BadCredentials(
                msg="token is empty. Check that REPOBEE_TOKEN environment "
                "variable is properly set, or supply the `--token` option."
            )

        g = github.Github(login_or_token=token, base_url=base_url)

        LOGGER.info("Trying to fetch user information ...")

        user_not_found_msg = (
            "user {} could not be found. Possible reasons: "
            "bad base url, bad username or bad access token permissions"
        ).format(user)
        with _convert_404_to_not_found_error(user_not_found_msg):
            user_ = g.get_user(user)
            msg = (
                "Specified login is {}, "
                "but the fetched user's login is {}.".format(user, user_.login)
            )
            if user_.login is None:
                msg = (
                    "{} Possible reasons: bad api url that points to a "
                    "GitHub instance, but not to the api endpoint."
                ).format(msg)
                raise exception.UnexpectedException(msg=msg)
            elif user_.login != user:
                msg = (
                    "{} Possible reasons: unknown, rerun with -tb and open an "
                    "issue on GitHub.".format(msg)
                )
                raise exception.UnexpectedException(msg=msg)
        LOGGER.info(
            "SUCCESS: found user {}, "
            "user exists and base url looks okay".format(user)
        )

        LOGGER.info("Verifying access token scopes ...")
        scopes = g.oauth_scopes
        if not REQUIRED_TOKEN_SCOPES.issubset(scopes):
            raise exception.BadCredentials(
                "missing one or more access token scopes. "
                "Actual: {}. Required {}".format(scopes, REQUIRED_TOKEN_SCOPES)
            )
        LOGGER.info("SUCCESS: access token scopes look okay")

        GitHubAPI._verify_org(org_name, user, g)
        if master_org_name:
            GitHubAPI._verify_org(master_org_name, user, g)

        LOGGER.info("GREAT SUCCESS: all settings check out!")

    @staticmethod
    def _verify_org(org_name: str, user: str, g: github.MainClass.Github):
        """Check that the organization exists and that the user is an owner."""
        LOGGER.info("Trying to fetch organization {} ...".format(org_name))
        org_not_found_msg = (
            "organization {} could not be found. Possible "
            "reasons: org does not exist, user does not have "
            "sufficient access to organization."
        ).format(org_name)
        with _convert_404_to_not_found_error(org_not_found_msg):
            org = g.get_organization(org_name)
        LOGGER.info("SUCCESS: found organization {}".format(org_name))

        LOGGER.info(
            "Verifying that user {} is an owner of organization {}".format(
                user, org_name
            )
        )
        owner_usernames = (
            owner.login for owner in org.get_members(role="admin")
        )
        if user not in owner_usernames:
            raise exception.BadCredentials(
                "user {} is not an owner of organization {}".format(
                    user, org_name
                )
            )
        LOGGER.info(
            "SUCCESS: user {} is an owner of organization {}".format(
                user, org_name
            )
        )


class DefaultAPIHooks(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "token", "org_name", "user")

    def get_api_class(self):
        return GitHubAPI
