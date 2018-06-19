"""Wrapper module for the GitHub API.

This module currently wraps PyGithub commands. The purpose of the module is to
make it easy to swap out PyGithub at a later date.

.. important: The setup_api function _must_ be called before any functions in
this module are called.

"""
import contextlib
import collections
from itertools import chan
from typing import List, Iterable, Mapping
import github

_API = None

Team = collections.namedtuple('Team', ('name', 'members', 'id'))
User = collections.namedtuple('User', ('username', 'id'))


class GitHubError(Exception):
    """An exception raised when the API responds with an error code."""


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
            raise NotFoundError(str(e))
        else:
            raise GitHubError(str(e))
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
        with _try_api_request():
            org.create_team(team_name, permission='push')

    with _try_api_request():
        teams = [
            team for team in org.get_teams()
            if team.name in required_team_names
        ]
    return teams


def add_to_teams(member_lists: Mapping[str, Iterable[str]],
                 org_name: str) -> List[Team]:
    """Add members to teams. Duplicates are ignored.
    
    Args:
        member_list: A mapping of (team_name, member_list) mappings.
        org_name: Name of an organization.

    Returns:
        A list of Team namedtuples of the teams corresponding to the keys of
        the member_lists mapping.
    """
    teams = _ensure_teams_exist(
        [team_name for team_name in member_lists.keys()], org_name)

    for team in teams:
        required_members = set(member_lists[team.name])
        existing_members = set(team.get_members())

        for username in required_members - existing_members:
            try:
                member = _API.get_user(username)
                team.add_membership(member)
            except github.GithubException as exc:
                # TODO log
                if exc.status != 404:
                    raise GitHubError(
                        "Got unexpected response code {} from the GitHub API".
                        format(exc.status))

    with _try_api_request():
        team_wrappers = [
            Team(
                name=team.name,
                members=[m.name for m in team.get_members()],
                id=team.id) for team in teams
        ]
    return team_wrappers
