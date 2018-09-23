"""Contains a wrapper class for the PyGithub library.

:py:class:`PyGithubWrapper` is a wrapper class that implements the
:py:class:`AbstractAPIWrapper` class and thereby provides a means of
interacting with a GitHub instance's API. As the name suggests, the underlying
library is PyGithub.

The point of this abstraction layer can be read about in the
:py:mod:`abstract_api_wrapper` module.

.. module:: pygithub_wrapper
    :synopsis: Contains a wrapper class for the PyGithub library.

.. moduleauthor:: Simon Larsén
"""

import contextlib
import collections
import re
from typing import Iterable, Mapping, Optional, List, Generator, Union
from socket import gaierror
import daiquiri
import github

from repomate import exception
from repomate import util
from repomate import tuples
from repomate.abstract_api_wrapper import AbstractAPIWrapper, REQUIRED_OAUTH_SCOPES

LOGGER = daiquiri.getLogger(__file__)

# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository


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
                type(exc), str(exc)))


@contextlib.contextmanager
def _try_api_request(ignore_statuses: Union[None, Iterable[int]] = None):
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
    except github.GithubException as e:
        if ignore_statuses and e.status in ignore_statuses:
            return

        if e.status == 404:
            raise exception.NotFoundError(str(e), status=404)
        elif e.status == 401:
            raise exception.BadCredentials(
                "credentials were rejected, verify that token has correct access.",
                status=401)
        else:
            raise exception.GitHubError(str(e), status=e.status)
    except gaierror as e:
        raise exception.ServiceNotFoundError(
            "GitHub service could not be found, check the url")
    except Exception as e:
        raise exception.UnexpectedException(
            "a {} occured unexpectedly: {}".format(type(e).__name__, str(e)))


class PyGithubWrapper(AbstractAPIWrapper):
    """APIWrapper implement on top of PyGithub."""

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

    def get_teams(self) -> Generator[tuples.Team, None, None]:
        """Returns: A generator of the organization's teams."""
        with _try_api_request():
            return (tuples.Team(
                name=team.name, members=team.get_members(), id=team.id)
                    for team in self._org.get_teams())

    def get_teams_in(self, team_names: Iterable[str]) -> List[tuples.Team]:
        """Get all teams that match any team name in the team_names iterable.

        Args:
            team_names: An iterable of team names.
        Returns:
            An iterable of Team namedtuples of all teams that matched any of the team names.
        """
        team_names = set(team_names)
        with _try_api_request():
            teams = [
                team for team in self.get_teams() if team.name in team_names
            ]
            return teams

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
                    raise exception.GitHubError(
                        "Got unexpected response code from the GitHub API",
                        status=exc.status)
                LOGGER.warning("user {} does not exist".format(name))
        return existing_users

    def add_to_team(self, members: Iterable[str], team: tuples.Team):
        """Add members to a team.

        Args:
            members: Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            team = self._org.get_team(team.id)
            users = self._get_users(members)
            for user in users:
                team.add_membership(user)

    def open_issue_in(self, issue: tuples.Issue,
                      repo_names: Iterable[str]) -> None:
        """Open issues in all repos defined by repo_names, if they exist.
        Skip any repos that do not exist.

        Args:
            issue: The issue to open.
            repo_names: Names of repos in the target organization.
        """
        repo_names_set = set(repo_names)
        repos = list(self._get_repos_by_name(repo_names_set))
        for repo in repos:
            with _try_api_request():
                created_issue = repo.create_issue(issue.title, body=issue.body)
            LOGGER.info("Opened issue {}/#{}-'{}'".format(
                repo.name, created_issue.number, created_issue.title))

    def close_issue_in(self, title_regex: str,
                       repo_names: Iterable[str]) -> None:
        """Close issues whose titles match the title_regex, in all repos
        defined by repo_names. Repos that do not exist are skipped.

        Args:
            title_regex: A regex to match against issue titles.
            repo_names: Names of repositories to close issues in.
        """
        repo_names_set = set(repo_names)
        repos = list(self._get_repos_by_name(repo_names_set))

        issue_repo_gen = ((issue, repo) for repo in repos
                          for issue in repo.get_issues(state='open')
                          if re.match(title_regex, issue.title))
        closed = 0
        for issue, repo in issue_repo_gen:
            issue.edit(state='closed')
            LOGGER.info("closed issue {}/#{}-'{}'".format(
                repo.name, issue.number, issue.title))
            closed += 1

        if not closed:
            LOGGER.warning("Found no matching issues.")

    def get_repo_url(self, repo_name: str) -> str:
        """Get a repo from the organization.
        
        Args:
            repo_name: Name of a repo.

        Returns:
            url to the repo, if it exists in the target organization.
        """
        with _try_api_request():
            return self._org.get_repo(repo_name).html_url

    @property
    def org_url(self) -> str:
        """Get the url to the target organization.

        Returns:
            url to the target organization.
        """
        return self._org.html_url

    def create_repo(self, repo: tuples.Repo):
        """Create a repo in the organization.

        Args:
            repo: A Repo namedtuple with repo attributes.

        Returns:
            The html url to the repo.
        """
        with _try_api_request():
            repo = self._org.create_repo(
                repo.name,
                description=repo.description,
                private=repo.private,
                team_id=repo.team_id)
        return repo.html_url

    def create_team(self, team_name: str, permission: str = 'push') -> None:
        """Create a team in the organization.

        Args:
            team_name: Name for the team.
            permission: The default access permission of the team.

        Returns:
            The created team.
        """
        with _try_api_request():
            self._org.create_team(team_name, permission=permission)

    def get_repos(self, repo_names: Optional[Iterable[str]] = None
                  ) -> Generator[tuples.Repo, None, None]:
        """Get repo objects for all repositories in the organization. If
        repo_names are supplied, fetches only repos that correspond with
        these names.

        Args:
            repo_names: An optional iterable of repo names.

        Returns:
            a generator of repo objects.
        """
        with _try_api_request():
            if repo_names:
                return (self._repo_factory(repo)
                        for repo in self._get_repos_by_name(repo_names))
            return (self._repo_factory(repo) for repo in self._org.get_repos())

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
        repos = self._get_repos_by_name(repo_names)

        with _try_api_request():
            name_issues_pairs = ((repo.name,
                                  (issue
                                   for issue in repo.get_issues(state=state) if
                                   re.match(title_regex or "", issue.title)))
                                 for repo in repos)

            for (repo_name, pygh_issues) in name_issues_pairs:
                issues = (tuples.Issue(
                    title=issue.title,
                    body=issue.body,
                    number=issue.number,
                    created_at=issue.created_at,
                    author=issue.user.login) for issue in pygh_issues)
                yield repo_name, issues

    def _repo_factory(self, repo: github.Repository.Repository) -> tuples.Repo:
        """Create a tuples.Repo object from a Repository object. Warn if
        there is anything but exactly one team affiliated with the repo.

        Args:
            repo: A Repository object.
        Returns:
            a tuples.Repo object representing the repo.
        """
        teams = list(repo.get_teams())
        if len(teams) != 1:
            LOGGER.warning(
                "expected {} to have exactly 1 team affiliation, found {}".
                format(repo.name, len(teams)))
        return tuples.Repo(
            name=repo.name,
            description=repo.description,
            private=repo.private,
            team_id=teams[0].id if teams else None,
            url=repo.html_url)

    def _get_repos_by_name(
            self, repo_names: Iterable[str]) -> Generator[_Repo, None, None]:
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
            LOGGER.warning("can't find repos: {}".format(
                ", ".join(missing_repos)))

    @staticmethod
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
        LOGGER.info("verifying settings ...")
        if not token:
            raise exception.BadCredentials(
                msg="token is empty. Check that REPOMATE_OAUTH environment "
                "variable is properly set.")

        util.validate_types(
            base_url=(base_url, str),
            token=(token, str),
            user=(user, str),
            org_name=(org_name, str))
        util.validate_non_empty(
            base_url=base_url, token=token, user=user, org_name=org_name)

        g = github.Github(login_or_token=token, base_url=base_url)

        LOGGER.info("trying to fetch user information ...")

        user_not_found_msg = (
            "user {} could not be found. Possible reasons: "
            "bad base url, bad username or bad oauth permissions").format(user)
        with _convert_404_to_not_found_error(user_not_found_msg):
            g.get_user(user)
        LOGGER.info(
            "SUCCESS: found user {}, user exists and base url looks okay".
            format(user))

        LOGGER.info("verifying oauth scopes ...")
        scopes = g.oauth_scopes
        if not REQUIRED_OAUTH_SCOPES.issubset(scopes):
            raise exception.BadCredentials(
                "missing one or more oauth scopes. Actual: {}. Required {}".
                format(scopes, REQUIRED_OAUTH_SCOPES))
        LOGGER.info("SUCCESS: oauth scopes look okay")

        LOGGER.info("trying to fetch organization ...")
        org_not_found_msg = (
            "organization {} could not be found. Possible "
            "reasons: org does not exist, user does not have "
            "sufficient access to organization.").format(org_name)
        with _convert_404_to_not_found_error(org_not_found_msg):
            org = g.get_organization(org_name)
        LOGGER.info("SUCCESS: found organization {}".format(org_name))

        LOGGER.info(
            "verifying that user {} is an owner of organization {}".format(
                user, org_name))
        owner_usernames = (owner.login
                           for owner in org.get_members(role='admin'))
        if user not in owner_usernames:
            raise exception.BadCredentials(
                "user {} is not an owner of organization {}".format(
                    user, org_name))
        LOGGER.info("SUCCESS: user {} is an owner of organization {}".format(
            user, org_name))

        LOGGER.info("GREAT SUCCESS: All settings check out!")
