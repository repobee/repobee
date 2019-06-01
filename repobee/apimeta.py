"""Metaclass for API implementations.

:py:class:`APIMeta` defines the behavior required of platform API
implementations, based on the methods in :py:class:`APISpec`. With platform
API, we mean for example the GitHub REST API, and the GitLab REST API. The
point is to introduce another layer of indirection such that higher levels of
RepoBee can use different platforms in a platform-independent way.
:py:class:`API` is a convenience class so consumers don't have to use the
metaclass directly.

Any class implementing a platform API should derive from :py:class:`API`. It
will enforce that all public methods are one of the method defined py
:py:class:`APISpec`, and give a default implementation (that just raises
NotImplementedError) for any unimplemented API methods.

.. module:: apimeta
    :synopsis: Metaclass for API implementations.

.. moduleauthor:: Simon Larsén
"""
import inspect
import collections
from typing import List, Iterable, Optional, Generator, Tuple, Mapping

import daiquiri

from repobee import exception
from repobee import tuples

LOGGER = daiquiri.getLogger(__file__)

MAX_NAME_LENGTH = 100


class APIObject:
    """Base wrapper class for platform API objects."""


def _check_name_length(name):
    """Check that a Team/Repository name does not exceed the maximum GitHub
    allows (100 characters)
    """
    if len(name) > MAX_NAME_LENGTH:
        LOGGER.error("Team/Repository name {} is too long".format(name))
        raise ValueError(
            "generated Team/Repository name is too long, was {} chars, "
            "max is {} chars".format(len(name), MAX_NAME_LENGTH)
        )
    elif len(name) > MAX_NAME_LENGTH * 0.8:
        LOGGER.warning(
            "Team/Repository name {} is {} chars long, close to the max of "
            "{} chars.".format(name, len(name), MAX_NAME_LENGTH)
        )


class Repo(
    APIObject,
    collections.namedtuple(
        "Repo", "name description private team_id url implementation".split()
    ),
):
    """Wrapper class for a Repo API object."""

    def __new__(
        cls,
        name,
        description,
        private,
        team_id=None,
        url=None,
        implementation=None,
    ):
        _check_name_length(name)
        return super().__new__(
            cls, name, description, private, team_id, url, implementation
        )


class Team(
    APIObject,
    collections.namedtuple("Repo", "name members id implementation".split()),
):
    """Wrapper class for a Team API object."""

    def __new__(cls, members, name=None, id=None, implementation=None):
        if not name:
            name = "-".join(sorted(members))
        _check_name_length(name)
        return super().__new__(cls, name, members, id, implementation)

    def __str__(self):
        return self.name


class Issue(
    APIObject,
    collections.namedtuple(
        "Issue", "title body number created_at author implementation".split()
    ),
):
    """Wrapper class for an Issue API object."""

    def __new__(
        cls,
        title,
        body,
        number=None,
        created_at=None,
        author=None,
        implementation=None,
    ):
        return super().__new__(
            cls, title, body, number, created_at, author, implementation
        )


class APISpec:
    """Wrapper class for API method stubs."""

    def __init__(self, base_url, token, org_name, user):
        _not_implemented()

    def ensure_teams_and_members(
        self, teams: Iterable[Team], permission: str
    ) -> List[Team]:
        """Ensure that the teams exist, and that their members are added to the
        teams.

        Teams that do not exist are created, teams that already exist are
        fetched. Members that are not in their teams are added, members that do
        not exist or are already in their teams are skipped.

        Args:
            teams: A list of teams specifying student groups.
        Returns:
            A list of Team API objects of the teams provided to the function,
            both those that were created and those that already existed.
        """
        _not_implemented()

    def get_teams(self) -> List[Team]:
        """Get all teams related to the target organization.

        Returns:
            A list of Team API object.
        """
        _not_implemented()

    def create_repos(self, repos: Iterable[Repo]) -> List[str]:
        """Create repos in the target organization according the those specced
        by the ``repos`` argument. Repos that already exist are skipped.

        Args:
            repos: Repos to be created.
        Returns:
            A list of urls to the repos specified by the ``repos`` argument,
            both those that were created and those that already existed.
        """
        _not_implemented()

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[Team]] = None,
    ) -> List[str]:
        """Get repo urls for all specified repo names in the organization. As
        checking if every single repo actually exists takes a long time with a
        typical REST API, this function does not in general guarantee that the
        urls returned actually correspond to existing repos.

        If the ``org_name`` argument is supplied, urls are computed relative to
        that organization. If it is not supplied, the target organization is
        used.

        If the `teams` argument is supplied, student repo urls are
        computed instead of master repo urls.

        Args:
            master_repo_names: A list of master repository names.
            org_name: Organization in which repos are expected. Defaults to the
                target organization of the API instance.
            teams: A list of teams specifying student groups. Defaults to None.
        Returns:
            a list of urls corresponding to the repo names.
        """
        _not_implemented()

    def get_issues(
        self,
        repo_names: Iterable[str],
        state: str = "open",
        title_regex: str = "",
    ) -> Generator[Tuple[str, Generator[Issue, None, None]], None, None]:
        """Get all issues for the repos in repo_names an return a generator
        that yields (repo_name, issue generator) tuples. Will by default only
        get open issues.

        Args:
            repo_names: An iterable of repo names.
            state: Specifying the state of the issue ('open', 'closed' or
            'all'). Defaults to 'open'.
            title_regex: If specified, only issues matching this regex are
            returned. Defaults to the empty string (which matches anything).
        Returns:
            A generator that yields (repo_name, issue_generator) tuples.
        """
        _not_implemented()

    def open_issue(
        self, title: str, body: str, repo_names: Iterable[str]
    ) -> None:
        """Open the specified issue in all repos with the given names, in the
        target organization.

        Args:
            title: Title of the issue.
            body: Body of the issue.
            repo_names: Names of repos to open the issue in.
        """
        _not_implemented()

    def close_issue(self, title_regex: str, repo_names: Iterable[str]) -> None:
        """Close any issues in the given repos in the target organization,
        whose titles match the title_regex.

        Args:
            title_regex: A regex to match against issue titles.
            repo_names: Names of repositories to close issues in.
        """
        _not_implemented()

    def add_repos_to_review_teams(
        self,
        team_to_repos: Mapping[str, Iterable[str]],
        issue: Optional[Issue] = None,
    ) -> None:
        """Add repos to review teams. For each repo, an issue is opened, and
        every user in the review team is assigned to it. If no issue is
        specified, sensible defaults for title and body are used.

        Args:
            team_to_repos: A mapping from a team name to an iterable of repo
                names.
            issue: An optional Issue tuple to override the default issue.
        """
        _not_implemented()

    def get_review_progress(
        self,
        review_team_names: Iterable[str],
        teams: Iterable[Team],
        title_regex: str,
    ) -> Mapping[str, List[tuples.Review]]:
        """Get the peer review progress for the specified review teams and
        student teams by checking which review team members have opened issues
        in their assigned repos. Only issues matching the title regex will be
        considered peer review issues. If a reviewer has opened an issue in the
        assigned repo with a title matching the regex, the review will be
        considered done.

        Note that reviews only count if the student is in the review team for
        that repo. Review teams must only have one associated repo, or the repo
        is skipped.

        Args:
            review_team_names: Names of review teams.
            teams: Team API objects specifying student groups.
            title_regex: If an issue title matches this regex, the issue is
                considered a potential peer review issue.
        Returns:
            a mapping (reviewer -> assigned_repos), where reviewer is a str and
            assigned_repos is a :py:class:`repobee.tuples.Review`.
        """
        _not_implemented()

    def delete_teams(self, team_names: Iterable[str]) -> None:
        """Delete all teams in the target organizatoin that exactly match one
        of the provided ``team_names``. Skip any team name for which no match
        is found.

        Args:
            team_names: A list of team names for teams to be deleted.
        """
        _not_implemented()

    @staticmethod
    def verify_settings(
        user: str,
        org_name: str,
        base_url: str,
        token: str,
        master_org_name: Optional[str] = None,
    ):
        """Verify the following (to the extent that is possible and makes sense
        for the specifi platform):

        1. Base url is correct
        2. The token has sufficient access privileges
        3. Target organization (specifiend by ``org_name``) exists
            - If master_org_name is supplied, this is also checked to
              exist.
        4. User is owner in organization (verify by getting
            - If master_org_name is supplied, user is also checked to be an
              owner of it.
        organization member list and checking roles)

        Should raise an appropriate subclass of
        :py:class:`repobee.exception.APIError` when a problem is encountered.

        Args:
            user: The username to try to fetch.
            org_name: Name of the target organization.
            base_url: A base url to a github API.
            token: A secure OAUTH2 token.
            org_name: Name of the master organization.
        Returns:
            True if the connection is well formed.
        Raises:
            :py:class:`repobee.exception.APIError`
        """
        _not_implemented()


def _not_implemented():
    raise NotImplementedError(
        "The chosen API does not currently support this functionality"
    )


def methods(attrdict):
    """Return all public methods and __init__ for some class."""
    return {
        name: method
        for name, method in attrdict.items()
        if callable(method)
        and not (name.startswith("_") or name == "__init__")
    }


def parameter_names(function):
    """Extract parameter names (in order) from a function."""
    return [
        param.name for param in inspect.signature(function).parameters.values()
    ]


def check_signature(reference, compare):
    """Check if the compared method matches the reference signature. Currently
    only checks parameter names and order of parameters.
    """
    reference_params = parameter_names(reference)
    compare_params = parameter_names(compare)
    if reference_params != compare_params:
        raise exception.APIImplementationError(
            "expected method '{}' to have parameters '{}', "
            "found '{}'".format(
                reference.__name__, reference_params, compare_params
            )
        )


class APIMeta(type):
    """Metaclass for an API implementation. All public methods must be a
    specified api method, but all api methods do not need to be implemented.
    Any unimplemented api method will be replaced with a default implementation
    that simply raises a NotImplementedError.
    """

    def __new__(cls, name, bases, attrdict):
        api_methods = methods(APISpec.__dict__)
        implemented_methods = methods(attrdict)
        non_api_methods = set(implemented_methods.keys()) - set(
            api_methods.keys()
        )
        if non_api_methods:
            raise exception.APIImplementationError(
                "non-API methods may not be public: {}".format(non_api_methods)
            )
        for method_name, method in api_methods.items():
            if method_name in implemented_methods:
                check_signature(method, implemented_methods[method_name])
            else:
                attrdict[method_name] = method
        return super().__new__(cls, name, bases, attrdict)


class API(metaclass=APIMeta):
    """API base class that all API implementations should inherit from."""
