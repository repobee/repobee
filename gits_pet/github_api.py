"""Wrapper module for the GitHub API.

This module currently wraps PyGithub commands. The purpose of the module is to
make it easy to swap out PyGithub at a later date.

.. important: The setup_api function _must_ be called before any functions in
this module are called.

"""
import contextlib
import collections
from typing import List, Iterable, Mapping
import daiquiri
import github

LOGGER = daiquiri.getLogger(__file__)

_API = None

Team = collections.namedtuple('Team', ('name', 'members', 'id'))
User = collections.namedtuple('User', ('username', 'id'))

RepoInfo = collections.namedtuple(
    'RepoInfo', ('name', 'description', 'private', 'team_id'))


class GitHubError(Exception):
    """An exception raised when the API responds with an error code."""

    def __init__(self, msg=None, status=None):
        self.status = status
        super().__init__(self, msg)


class NotFoundError(GitHubError):
    """An exception raised when the API responds with a 404."""


class UnexpectedException(GitHubError):
    """An exception raised when an API request raises an unexpected exception."""


@contextlib.contextmanager
def _try_api_request():
    """Context manager for trying API requests."""
    try:
        yield
    except github.GithubException as e:
        if e.status == 404:
            raise NotFoundError(str(e), status=404)
        else:
            raise GitHubError(str(e), status=e.status)
    except Exception as e:
        raise UnexpectedException("An unexpected exception occured. This is "
                                  "probably a bug, please report it.")


def setup_api(base_url: str, token: str):
    """Set up the GitHub API object. Must be called before any of the functions
    in this module are called!

    Args:
        base_url: The base url to a GitHub REST api (e.g.
        https://api.github.com for GitHub or https://<HOST>/api/v3 for
        Enterprise).
        token: A GitHub OAUTH token.
    """
    global _API
    _API = github.Github(login_or_token=token, base_url=base_url)


def _ensure_teams_exist(team_names: Iterable[str],
                        org_name: str) -> List[github.Team.Team]:
    """Ensure that teams with the given team names exist in the given
    organization. Create any that do not.
    
    Args:
        team_names: An iterable of team names.
        org_name: Name of an organization.

    Returns:
        A list of Team namedtuples representing the teams corresponding to the
        provided team_names.
    """
    assert _API
    with _try_api_request():
        org = _API.get_organization(org_name)
        existing_team_names = set(team.name for team in org.get_teams())

    required_team_names = set(team_names)
    for team_name in required_team_names - existing_team_names:
        try:
            org.create_team(team_name, permission='push')
            LOGGER.info("created team {}".format(team_name))
        except github.GithubException as exc:
            if exc.status != 422:
                raise UnexpectedException(str(exc))
            LOGGER.info("team {} already exists".format(team_name))

    with _try_api_request():
        teams = [
            team for team in org.get_teams()
            if team.name in required_team_names
        ]
    return teams


def ensure_teams_and_members(member_lists: Mapping[str, Iterable[str]],
                             org_name: str) -> List[Team]:
    """Ensure that each team exists and has its required members. If a team is
    does not exist or is missing any of the members in its member list, the team
    is created and/or missing members are added. Otherwise, nothing happens.
    
    Args:
        member_list: A mapping of (team_name, member_list) mappings.
        org_name: Name of an organization.

    Returns:
        A list of Team namedtuples of the teams corresponding to the keys of
        the member_lists mapping.
    """
    LOGGER.info("creating teams...")
    teams = _ensure_teams_exist(
        [team_name for team_name in member_lists.keys()], org_name)

    LOGGER.info("adding members to teams...")
    for team in teams:
        required_members = set(member_lists[team.name])
        existing_members = set(team.get_members())
        missing_members = required_members - existing_members

        if missing_members:
            LOGGER.info("adding members {} to team {}".format(
                ", ".join(missing_members), team.name))
        else:
            LOGGER.info("{} already in team {}, skipping team...".format(
                ", ".join(required_members), team.name))

        for username in missing_members:
            try:
                member = _API.get_user(username)
            except github.GithubException as exc:
                if exc.status != 404:
                    raise GitHubError(
                        "Got unexpected response code from the GitHub API",
                        status=exc.status)
                LOGGER.warning(
                    "user {} does not exist, skipping".format(username))

            with _try_api_request():
                team.add_membership(member)

    with _try_api_request():
        team_wrappers = [
            Team(
                name=team.name,
                members=[m.name for m in team.get_members()],
                id=team.id) for team in teams
        ]
    return team_wrappers


def create_repos(repo_infos: Iterable[RepoInfo], org_name: str):
    """Create repositories in the given organization according to the RepoInfos.
    Repos that already exist are skipped.

    Args:
        repo_infos: An iterable of RepoInfo namedtuples.
        org_name: Name of an organization.

    Returns:
        A list of urls to all repos corresponding to the RepoInfos.
    """
    assert _API
    with _try_api_request():
        org = _API.get_organization(org_name)

    repo_urls = []
    for info in repo_infos:
        try:
            repo_urls.append(_create_repo(info, org))
            LOGGER.info("created {}/{}".format(org_name, info.name))
        except GitHubError as exc:
            if exc.status != 422:
                raise UnexpectedException(
                    "Got unexpected response code {} from the GitHub API".
                    format(exc.status))
            LOGGER.info("{}/{} already exists".format(org_name, info.name))
            repo_urls.append(_get_repo_url(info.name, org))
        except Exception as exc:
            raise UnexpectedException("An unexpected exception was raised.")
    return repo_urls


def _create_repo(repo_info: RepoInfo,
                 org: github.Organization.Organization) -> str:
    """Create a single repo and return its url.

    Args:
        repo_info: A RepoInfo namedtuple.
        org: A github.Organization.Organization.
    """
    with _try_api_request():
        repo = org.create_repo(
            repo_info.name,
            description=repo_info.description,
            private=repo_info.private,
            team_id=repo_info.team_id)
    return repo.html_url


def _get_repo_url(repo_name: str,
                  org: github.Organization.Organization) -> str:
    """
    Args:
        repo_name: Name of a repository.
        org: An Organization object.

    Returns:
        The html url to the repo.
    """
    return org.get_repo(repo_name).html_url
