"""GitHub API module.

This module contains the :py:class:`GitHubAPI` class, which is meant to be the
prime means of interacting with the GitHub API in ``repomate``. The methods of
GitHubAPI are mostly high-level bulk operations.

.. module:: github_api
    :synopsis: Top level interface for interacting with a GitHub instance within repomate.

.. moduleauthor:: Simon Larsén
"""
import re
import os
from typing import List, Iterable, Mapping, Union, Optional, Generator, Tuple
from socket import gaierror
import collections
import daiquiri
import contextlib
import github

from repomate import exception
from repomate import tuples
from repomate import util

REQUIRED_OAUTH_SCOPES = {'admin:org', 'repo'}

LOGGER = daiquiri.getLogger(__file__)

# classes used internally in this module
_Team = github.Team.Team
_User = github.NamedUser.NamedUser
_Repo = github.Repository.Repository

DEFAULT_REVIEW_ISSUE = tuples.Issue(
    title="Peer review",
    body="You have been assigned to peer review this repo.")


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
        self._github = github.Github(login_or_token=token, base_url=base_url)
        with _try_api_request():
            self._org = self._github.get_organization(org_name)
        self._org_name = org_name
        self._base_url = base_url
        self._token = token

    def __repr__(self):
        return "GitHubAPI(base_url={}, token={}, org_name={})".format(
            self._base_url, self._token, self._org_name)

    @property
    def org(self):
        return self._org

    def get_teams_in(self, team_names: Iterable[str]
                     ) -> Generator[github.Team.Team, None, None]:
        """Get all teams that match any team name in the team_names iterable.

        Args:
            team_names: An iterable of team names.
        Returns:
            An iterable of Team namedtuples of all teams that matched any of the team names.
        """
        team_names = set(team_names)
        with _try_api_request():
            yield from (team for team in self.org.get_teams()
                        if team.name in team_names)

    def delete_teams(self, team_names: Iterable[str]) -> None:
        """Delete all teams that match any of the team names. Skip any team
        name for which no team can be found.

        Args:
            team_names: A list of team names for teams to be deleted.
        """
        deleted = set()  # only for logging
        for team in self.get_teams_in(team_names):
            team.delete()
            deleted.add(team.name)
            LOGGER.info("deleted team {}".format(team.name))

        # only logging
        missing = set(team_names) - deleted
        if missing:
            LOGGER.warning("could not find teams: {}".format(
                ", ".join(missing)))

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

    def ensure_teams_and_members(
            self,
            member_lists: Mapping[str, Iterable[str]],
            permission: str = 'push') -> List[tuples.Team]:
        """Create teams that do not exist and add members not in their
        specified teams (if they exist as users).

        Args:
            member_list: A mapping of (team_name, member_list).

        Returns:
            A list of Team namedtuples of the teams corresponding to the keys of
            the member_lists mapping.
        """
        teams = self._ensure_teams_exist(
            [team_name for team_name in member_lists.keys()],
            permission=permission)

        for team in [team for team in teams if member_lists[team.name]]:
            self._ensure_members_in_team(team, member_lists[team.name])

        return list(self.get_teams_in(set(member_lists.keys())))

    def _ensure_teams_exist(self,
                            team_names: Iterable[str],
                            permission: str = 'push') -> List[tuples.Team]:
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
        existing_teams = list(self._org.get_teams())
        existing_team_names = set(team.name for team in existing_teams)

        required_team_names = set(team_names)
        teams = [
            team for team in existing_teams if team.name in required_team_names
        ]

        for team_name in required_team_names - existing_team_names:
            with _try_api_request():
                new_team = self._org.create_team(
                    team_name, permission=permission)
                LOGGER.info("created team {}".format(team_name))
                teams.append(new_team)
        return teams

    def _ensure_members_in_team(self, team: github.Team.Team,
                                members: Iterable[str]):
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
            LOGGER.info("adding members {} to team {}".format(
                ", ".join(missing_members), team.name))
        if existing_members:
            LOGGER.info("{} already in team {}, skipping...".format(
                ", ".join(existing_members), team.name))
        self.add_to_team(missing_members, team)

    def add_to_team(self, members: Iterable[str], team: github.Team.Team):
        """Add members to a team.

        Args:
            members: Users to add to the team.
            team: A Team.
        """
        with _try_api_request():
            users = self._get_users(members)
            for user in users:
                team.add_membership(user)

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
            with _try_api_request(ignore_statuses=[422]):
                repo_urls.append(
                    self._org.create_repo(
                        info.name,
                        description=info.description,
                        private=info.private,
                        team_id=info.team_id,
                    ).html_url)
                LOGGER.info("created {}/{}".format(self._org_name, info.name))
                created = True

            if not created:
                repo_urls.append(self._org.get_repo(info.name).html_url)
                LOGGER.info("{}/{} already exists".format(
                    self._org_name, info.name))

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
            "{}/{}".format(self._org.html_url, repo_name)
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
        repos = self._get_repos_by_name(repo_names)

        with _try_api_request():
            name_issues_pairs = ((repo.name, (
                issue for issue in repo.get_issues(state=state)
                if re.match(title_regex or "", issue.title)))
                                 for repo in repos)
        yield from name_issues_pairs

    def open_issue(self, title: str, body: str,
                   repo_names: Iterable[str]) -> None:
        """Open the specified issue in all repos with the given names.

        Args:
            title: Title of the issue.
            body: Body of the issue.
            repo_names: Names of repos to open the issue in.
        """
        repo_names_set = set(repo_names)
        repos = list(self._get_repos_by_name(repo_names_set))
        for repo in repos:
            with _try_api_request():
                created_issue = repo.create_issue(title, body=body)
            LOGGER.info("Opened issue {}/#{}-'{}'".format(
                repo.name, created_issue.number, created_issue.title))

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """Close any issues in the given repos whose titles match the title_regex.

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

    def add_repos_to_review_teams(self,
                                  team_to_repos: Mapping[str, Iterable[str]],
                                  issue: Optional[tuples.Issue]) -> None:
        """Add repos to review teams. For each repo, an issue is opened, and
        every user in the review team is assigned to it. If no issue is
        specified, sensible defaults for title and body are used.

        Args:
            team_to_repos: A mapping from a team name to a sequence of repo names.
            issue: An an optional Issue tuple to override the default issue.
        """
        issue = issue or DEFAULT_REVIEW_ISSUE
        for team, repo in self.add_repos_to_teams(team_to_repos):
            # TODO team.get_members() api request is a bit redundant, it
            # can be solved in a more efficient way by passing in the
            # allocations
            reviewers = team.get_members()
            created_issue = repo.create_issue(
                issue.title, body=issue.body, assignees=reviewers)
            LOGGER.info("opened issue {}/#{}-'{}'".format(
                repo.name, created_issue.number, created_issue.title))

    def get_review_progress(self, review_team_names, students,
                            title_regex) -> Mapping[str, List[tuples.Review]]:
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
            assigned_repos is a :py:class:`~repomate.tuples.Review`.
        """
        reviews = collections.defaultdict(list)
        teams = self.get_teams_in(review_team_names)
        for team in teams:
            with _try_api_request():
                LOGGER.info("processing {}".format(team.name))
                reviewers = set(m.login for m in team.get_members())
                repos = list(team.get_repos())
                if len(repos) != 1:
                    LOGGER.warning(
                        "expected {} to have 1 associated repo, found {}. Skipping..."
                        .format(team.name, len(repos)))
                    continue

                repo = repos[0]
                review_issue_authors = {
                    issue.user.login
                    for issue in repo.get_issues()
                    if re.match(title_regex, issue.title)
                }

                for reviewer in reviewers:
                    reviews[reviewer].append(
                        tuples.Review(
                            repo=repo.name,
                            done=reviewer in review_issue_authors))

        return reviews

    def add_repos_to_teams(
            self, team_to_repos: Mapping[str, Iterable[str]]
    ) -> Generator[Tuple[github.Team.Team, github.Repository.
                         Repository], None, None]:
        """Add repos to teams and yield each (team, repo) combination _after_
        the repo has been added to the team.

        Args:
            team_to_repos: A mapping from a team name to a sequence of repo names.
        Returns:
            a generator yielding each (team, repo) tuple in turn.
        """
        team_names = set(team_to_repos.keys())
        with _try_api_request():
            teams = (team for team in self._org.get_teams()
                     if team.name in team_names)
        for team in teams:
            repos = self._get_repos_by_name(team_to_repos[team.name])
            for repo in repos:
                LOGGER.info("adding team {} to repo {} with '{}' permission"\
                        .format(team.name, repo.name, team.permission))
                with _try_api_request():
                    team.add_to_repos(repo)
                yield team, repo

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
            user_ = g.get_user(user)
            msg = "specified login is {}, but the fetched user's login is {}.".format(
                user, user_.login)
            if user_.login is None:
                msg = ("{} Possible reasons: bad api url that points to a "
                       "GitHub instance, but not to the api endpoint."
                       ).format(msg)
                raise exception.UnexpectedException(msg=msg)
            elif user_.login != user:
                msg = (
                    "{} Possible reasons: unknown, rerun with -tb and open an "
                    "issue on GitHub.".format(msg))
                raise exception.UnexpectedException(msg=msg)
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
