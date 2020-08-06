"""GitHub API module.

This module contains the :py:class:`GitHubAPI` class, which is meant to be the
prime means of interacting with the GitHub API in ``repobee``. The methods of
GitHubAPI are mostly high-level bulk operations.

.. module:: github
    :synopsis: Top level interface for interacting with a GitHub instance
        within _repobee.

.. moduleauthor:: Simon Larsén
"""
import pathlib
from typing import List, Iterable, Optional, Generator
from socket import gaierror
import contextlib

import daiquiri
import github

import repobee_plug as plug

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
    plug.NotFoundError with the provided message. If the GithubException
    does not have status 404, instead raise plug.UnexpectedException.
    """
    try:
        yield
    except github.GithubException as exc:
        if exc.status == 404:
            raise plug.NotFoundError(msg)
        raise plug.UnexpectedException(
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
        plug.NotFoundError
        plug.BadCredentials
        plug.APIError
        plug.ServiceNotFoundError
        plug.UnexpectedException
    """
    try:
        yield
    except github.GithubException as e:
        if ignore_statuses and e.status in ignore_statuses:
            return

        if e.status == 404:
            raise plug.NotFoundError(str(e), status=404)
        elif e.status == 401:
            raise plug.BadCredentials(
                "credentials rejected, verify that token has correct access.",
                status=401,
            )
        else:
            raise plug.APIError(str(e), status=e.status)
    except gaierror:
        raise plug.ServiceNotFoundError(
            "GitHub service could not be found, check the url"
        )
    except Exception as e:
        raise plug.UnexpectedException(
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

    # START EXPERIMENTAL API

    def create_team(
        self,
        name: str,
        members: Optional[List[str]] = None,
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> plug.Team:
        with _try_api_request():
            team = self._org.create_team(
                name, permission=_TEAM_PERMISSION_MAPPING[permission]
            )
            # remove the creator and any other default members from the team
            for member in team.get_members():
                team.remove_membership(member)

        # TODO optimize, redundant API call when wrapping the team
        self.assign_members(self._wrap_team(team), members, permission)

        return self._wrap_team(team)

    def assign_members(
        self,
        team: plug.Team,
        members: List[str],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> None:
        assert team.implementation

        with _try_api_request():
            users = self._get_users(members)
            for user in users:
                team.implementation.add_membership(
                    user,
                    role="maintainer"
                    if permission == plug.TeamPermission.PUSH
                    else "member",
                )

    def assign_repo(
        self, team: plug.Team, repo: plug.Repo, permission: plug.TeamPermission
    ) -> None:
        team.implementation.add_to_repos(repo.implementation)
        team.implementation.set_repo_permission(
            repo.implementation, _TEAM_PERMISSION_MAPPING[permission]
        )

    def create_repo(
        self,
        name: str,
        description: str,
        private: bool,
        team: Optional[plug.Team] = None,
    ) -> plug.Repo:
        kwargs = dict(description=description, private=private)
        if team:
            kwargs["team_id"] = team.id

        with _try_api_request():
            repo = self._org.create_repo(name, **kwargs)
            return self._wrap_repo(repo)

    def get_repo(
        self,
        repo_name: str,
        team_name: Optional[str],
        include_issues: Optional[plug.IssueState] = None,
    ) -> plug.Repo:
        # the GitHub API does not need the team name, as teams do not form
        # namespaces
        repo = self._org.get_repo(repo_name)
        return self._wrap_repo(repo, include_issues=include_issues)

    def get_teams(
        self,
        team_names: Optional[List[str]] = None,
        include_repos: bool = False,
        include_issues: Optional[plug.IssueState] = None,
    ) -> Iterable[plug.Team]:
        assert not include_issues or include_repos

        team_names = set(team_names)
        with _try_api_request():
            return (
                self._wrap_team(
                    team,
                    include_repos=include_repos,
                    include_issues=include_issues,
                )
                for team in self._org.get_teams()
                if not team_names or team.name in team_names
            )

    def get_repos(
        self,
        repo_names: Optional[List[str]] = None,
        include_issues: Optional[plug.IssueState] = None,
    ) -> Iterable[plug.Repo]:
        return (
            self._wrap_repo(repo, include_issues)
            for repo in self._get_repos_by_name(repo_names or [])
        )

    def create_issue(
        self,
        title: str,
        body: str,
        repo: plug.Repo,
        assignees: Optional[str] = None,
    ) -> plug.Issue:
        repo_impl: github.Repository.Repository = repo.implementation
        issue = repo_impl.create_issue(title, body=body, assignees=assignees)
        return self._wrap_issue(issue)

    def close_issue(self, issue: plug.Issue) -> None:
        issue.implementation.edit(state="closed")

    def delete_team(self, team: plug.Team) -> None:
        team.implementation.delete()

    def refresh_team(
        self,
        team: plug.Team,
        include_repos: bool = False,
        include_issues: Optional[plug.IssueState] = None,
    ) -> plug.Repo:
        return self._wrap_team(
            team.implementation,
            include_repos=include_repos,
            include_issues=include_issues,
        )

    def refresh_repo(
        self, repo: plug.Repo, include_issues: Optional[plug.IssueState] = None
    ) -> plug.Repo:
        return self._wrap_repo(
            repo.implementation, include_issues=include_issues
        )

    def _wrap_team(
        self,
        team: _Team,
        include_repos: bool = False,
        include_issues: Optional[plug.TeamPermission] = None,
    ) -> plug.Team:
        assert not include_issues or include_repos

        repos = (
            [
                self._wrap_repo(repo, include_issues=include_issues)
                for repo in team.get_repos()
            ]
            if include_repos
            else None
        )
        return plug.Team(
            name=team.name,
            members=[m.login for m in team.get_members()],
            id=team.id,
            repos=repos,
            implementation=team,
        )

    def _wrap_repo(
        self,
        repo: _Repo,
        include_issues: Optional[plug.TeamPermission] = None,
    ) -> plug.Repo:
        issues = (
            [
                self._wrap_issue(issue)
                for issue in repo.get_issues(
                    state=_ISSUE_STATE_MAPPING[include_issues]
                )
            ]
            if include_issues
            else None
        )
        return plug.Repo(
            name=repo.name,
            description=repo.description,
            private=repo.private,
            url=repo.html_url,
            issues=issues,
            implementation=repo,
        )

    def _wrap_issue(self, issue: github.Issue.Issue) -> plug.Issue:
        return plug.Issue(
            title=issue.title,
            body=issue.body,
            number=issue.number,
            created_at=issue.created_at.isoformat(),
            author=issue.user.login,
            implementation=issue,
        )

    # END EXPERIMENTAL API

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
                    raise plug.APIError(
                        "Got unexpected response code from the GitHub API",
                        status=exc.status,
                    )
                LOGGER.warning("User {} does not exist".format(name))
        return existing_users

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[plug.Team]] = None,
        insert_auth: bool = False,
    ) -> List[str]:
        """See :py:meth:`repobee_plug.API.get_repo_urls`."""
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
            self.insert_auth(url) if insert_auth else url
            for url in (
                "{}/{}".format(org.html_url, repo_name)
                for repo_name in list(repo_names)
            )
        ]

    def extract_repo_name(self, repo_url: str) -> str:
        """See :py:meth:`repobee_plug.API.extract_repo_name`."""
        return pathlib.Path(repo_url).stem

    def insert_auth(self, url: str) -> str:
        """Insert an authentication token into the url.

        Args:
            repo_url: A HTTPS url to a repository.
        Returns:
            the input url with an authentication token inserted.
        """
        if not url.startswith("https://"):
            raise ValueError(
                f"unsupported protocol in '{url}', please use https://"
            )
        auth = "{}:{}".format(self._user, self.token)
        return url.replace("https://", f"https://{auth}@")

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

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ) -> None:
        """See :py:meth:`repobee_plug.API.verify_settings`."""
        LOGGER.info("Verifying settings ...")
        if not token:
            raise plug.BadCredentials(
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
                raise plug.UnexpectedException(msg=msg)
            elif user_.login != user:
                msg = (
                    "{} Possible reasons: unknown, rerun with -tb and open an "
                    "issue on GitHub.".format(msg)
                )
                raise plug.UnexpectedException(msg=msg)
        LOGGER.info(
            "SUCCESS: found user {}, "
            "user exists and base url looks okay".format(user)
        )

        LOGGER.info("Verifying access token scopes ...")
        scopes = g.oauth_scopes
        if not REQUIRED_TOKEN_SCOPES.issubset(scopes):
            raise plug.BadCredentials(
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
            raise plug.BadCredentials(
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
