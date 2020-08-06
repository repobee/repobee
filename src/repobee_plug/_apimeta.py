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
import dataclasses
import inspect
import enum
import itertools
from typing import List, Iterable, Optional, Any

from repobee_plug import _exceptions

MAX_NAME_LENGTH = 100


class APIObject:
    """Base wrapper class for platform API objects."""

    def __getattribute__(self, name: str):
        """If the sought attr is 'implementation', and that attribute is None,
        an AttributeError should be raise. This is because there should never
        be a case where the caller tries to access a None implementation: if
        it's None the caller should now without checking, as only API objects
        returned by platform API (i.e. a class deriving from :py:class:`API`)
        can have a reasonable value for the implementation attribute.

        In all other cases, proceed as usual in getting the attribute. This
        includes the case when ``name == "implementation"``, and the APIObject
        does not have that attribute.
        """
        attr = object.__getattribute__(self, name)
        if attr is None and name == "implementation":
            raise AttributeError(
                "invalid access to 'implementation': not initialized"
            )
        return attr


class TeamPermission(enum.Enum):
    """Enum specifying team permissions on creating teams. On GitHub, for
    example, this can be e.g. `push` or `pull`.
    """

    PUSH = "push"
    PULL = "pull"


class IssueState(enum.Enum):
    """Enum specifying a possible issue state."""

    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


def _check_name_length(name):
    """Check that a Team/Repository name does not exceed the maximum GitHub
    allows (100 characters)
    """
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(
            "generated Team/Repository name is too long, was {} chars, "
            "max is {} chars".format(len(name), MAX_NAME_LENGTH)
        )


@dataclasses.dataclass
class Team(APIObject):
    """Wrapper class for a Team API object."""

    def __init__(
        self,
        members: Iterable[str],
        name: Optional[str] = None,
        id: Optional[Any] = None,
        repos: Optional[List["Repo"]] = None,
        implementation: Optional[Any] = None,
    ):
        self.members = list(members)
        self.name = name if name else "-".join(sorted(members))
        self.id = id
        self.repos = repos
        self.implementation = implementation

        _check_name_length(self.name)

    def __str__(self):
        return self.name

    def __lt__(self, o):
        return self.name < o.name


@dataclasses.dataclass
class Issue(APIObject):
    """Wrapper class for an Issue API object."""

    def __init__(
        self,
        title: str,
        body: str,
        number: Optional[int] = None,
        created_at: Optional[str] = None,
        author: Optional[str] = None,
        implementation: Optional[Any] = None,
    ):
        self.title = title
        self.body = body
        self.number = number
        self.created_at = created_at
        self.author = author
        self.implementation = implementation

    def to_dict(self):
        """Return a dictionary representation of this namedtuple, without
        the ``implementation`` field.
        """
        asdict = {
            "title": self.title,
            "body": self.body,
            "number": self.number,
            "created_at": self.created_at,
            "author": self.author,
        }
        return asdict

    @staticmethod
    def from_dict(asdict: dict) -> "Issue":
        """Take a dictionary produced by Issue.to_dict and reconstruct the
        corresponding instance. The ``implementation`` field is lost in a
        to_dict -> from_dict roundtrip.
        """
        return Issue(**asdict)


@dataclasses.dataclass
class Repo(APIObject):
    """Wrapper class for a Repo API object."""

    def __init__(
        self,
        name: str,
        description: str,
        private: bool,
        url: Optional[str] = None,
        issues: Optional[Iterable[Issue]] = None,
        implementation: Optional[Any] = None,
    ):
        _check_name_length(name)
        self.name = name
        self.description = description
        self.private = private
        self.url = url
        self.issues = issues
        self.implementation = implementation


class APISpec:
    """Wrapper class for API method stubs.

    .. important::

        This class should not be inherited from directly, it serves only to
        document the behavior of a platform API. Classes that implement this
        behavior should inherit from :py:class:`API`.
    """

    def __init__(self, base_url, token, org_name, user):
        _not_implemented()

    def create_team(
        self,
        name: str,
        members: Optional[List[str]] = None,
        permission: TeamPermission = TeamPermission.PUSH,
    ) -> Team:
        """Create a team on the platform.

        Args:
            name: Name of the team.
            members: A list of usernames to assign as members to this team.
                Usernames that don't exist are ignored.
            permission: The permission the team should have in regards to
                repository access.
        Returns:
            The created team.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform, in particular if the team
                already exists.
        """
        _not_implemented()

    def delete_team(self, team: Team) -> None:
        """Delete the provided team.

        Args:
            team: The team to delete.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def get_teams(
        self,
        team_names: Optional[List[str]] = None,
        include_repos: bool = False,
        include_issues: Optional[IssueState] = None,
    ) -> Iterable[Team]:
        """Get teams from the platform.

        Args:
            team_names: Team names to filter by. Names that do not exist on the
                platform are ignored. If ``team_names=None``, all teams are
                fetched.
            include_repos: Whether or not to also fetch associated
                repositories. This results in additional API requests.
            include_issues: The state of issues to fetch for the associated
                repos, or ``None`` if no issues should be included. Only makes
                sense if ``include_repos=True``. This results in additional API
                requests.
        Returns:
            Teams matching the filters.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def assign_repo(
        self, team: Team, repo: Repo, permission: TeamPermission,
    ) -> None:
        """Assign a repository to a team, granting any members of the team
        permission to access the repository according to the specified
        permission.

        Args:
            team: The team to assign the repository to.
            repo: The repository to assign to the team.
            permission: The permission granted to the team's members with
                respect to accessing the repository.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def assign_members(
        self,
        team: Team,
        members: List[str],
        permission: TeamPermission = TeamPermission.PUSH,
    ) -> None:
        """Assign members to a team.

        Args:
            team: A team to assign members to.
            members: A list of usernames to assign as members to the team.
                Usernames that don't exist are ignored.
            permission: The permission to add users with.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def create_repo(
        self,
        name: str,
        description: str,
        private: bool,
        team: Optional[Team] = None,
    ) -> Repo:
        """Create a repository.

        If the repository already exists, it is fetched instead of created.
        This somewhat unintuitive behavior is to speed up repository creation,
        as first checking if the repository exists can be a bit inconvenient
        and/or inefficient depending on the platform.

        Args:
            name: Name of the repository.
            description: Description of the repository.
            private: Visibility of the repository.
            team: The team the repository belongs to.
        Returns:
            The created (or fetched) repository.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def get_repos(
        self,
        repo_names: Optional[List[str]] = None,
        include_issues: Optional[IssueState] = None,
    ) -> Iterable[Repo]:
        """Get repositories from the platform.

        Args:
            repo_names: Repository names to filter the results by. Names that
                do not exist on the platform are ignored. If
                ``repo_names=None``, all repos are fetched.
            include_issues: The state of issues to fetch, or ``None`` if no
                issues should be included. Only makes sense if
                ``include_repos=True``. This results in additional API
                requests.
        Returns:
            Repositories matching the filters.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def get_repo(
        self,
        repo_name: str,
        team_name: Optional[str],
        include_issues: Optional[IssueState] = None,
    ) -> Repo:
        """Get a single repository.

        Args:
            repo_name: Name of the repository to fetch.
            team_name: Name of the team that owns the repository. If ``None``,
                the repository is assumed to belong to the target organization.
            include_issues: The state of issues to fetch, or ``None`` if no
                issues should be included. Only makes sense if
                ``include_repos=True``. This results in additional API
                requests.
        Returns:
            The fetched repository.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform, in particular if the repo
                or team does not exist.
        """
        _not_implemented()

    def insert_auth(self, url: str) -> str:
        """Insert authorization token into the provided URL.

        Args:
            url: A URL to the platform.
        Returns:
            The same url, but with authorization credentials inserted.
        """
        _not_implemented()

    def create_issue(
        self,
        title: str,
        body: str,
        repo: Repo,
        assignees: Optional[Iterable[str]] = None,
    ) -> Issue:
        """Create an issue in the provided repository.

        Args:
            title: Title of the issue.
            body: Body of the issue.
            repo: The repository in which to open the issue.
            assignees: Usernames to assign to the issue.
        Returns:
            The created issue.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def close_issue(self, issue: Issue) -> None:
        """Close the provided issue.

        Args:
            issue: The issue to close.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def refresh_repo(
        self, repo: Repo, include_issues: Optional[IssueState] = None
    ) -> Repo:
        """Refresh a repository by re-fetching information from the platform.

        Args:
            repo: A repository to refresh.
            include_issues: The state of issues to fetch, or ``None`` if no
                issues should be included. Only makes sense if
                ``include_repos=True``. This results in additional API
                requests.
        Returns:
            A refreshed version of the provided repository.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def refresh_team(
        self,
        team: Team,
        include_repos: bool = False,
        include_issues: Optional[IssueState] = None,
    ) -> Repo:
        """Refresh a team by re-fetching information from the platform.

        Args:
            team: A team to refresh.
            include_repos: Whether or not to also fetch associated
                repositories. This results in additional API requests.
            include_issues: The state of issues to fetch for the associated
                repos, or ``None`` if no issues should be included. Only makes
                sense if ``include_repos=True``. This results in additional API
                requests.
        Returns:
            A refreshed version of the provided repository.
        Raises:
            :py:class:`_exceptions.APIError`: If something goes wrong in
                communicating with the platform.
        """
        _not_implemented()

    def get_repo_urls(
        self,
        master_repo_names: Iterable[str],
        org_name: Optional[str] = None,
        teams: Optional[List[Team]] = None,
        insert_auth: bool = False,
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

    def extract_repo_name(self, repo_url: str) -> str:
        """Extract a repo name from the provided url.

        Args:
            repo_url: A URL to a repository.
        Returns:
            The name of the repository corresponding to the url.
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
        for the specific platform):

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
        :py:class:`~repobee_plug.APIError` when a problem is encountered.

        Args:
            user: The username to try to fetch.
            org_name: Name of the target organization.
            base_url: A base url to a github API.
            token: A secure OAUTH2 token.
            org_name: Name of the master organization.
        Returns:
            True if the connection is well formed.
        Raises:
            :py:class:`~repobee_plug.APIError`
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
        and (not name.startswith("_") or name == "__init__")
    }


def parameters(function):
    """Extract parameter names and default arguments from a function."""
    return [
        (param.name, param.default)
        for param in inspect.signature(function).parameters.values()
    ]


def check_init_params(reference_params, compare_params):
    """Check that the compare __init__'s parameters are a subset of the
    reference class's version.
    """
    extra = set(compare_params) - set(reference_params)
    if extra:
        raise _exceptions.APIImplementationError(
            "unexpected arguments to __init__: {}".format(extra)
        )


def check_parameters(reference, compare):
    """Check if the parameters match, one by one. Stop at the first diff and
    raise an exception for that parameter.

    An exception is made for __init__, for which the compare may be a subset of
    the reference in no particular order.
    """
    reference_params = parameters(reference)
    compare_params = parameters(compare)
    if reference.__name__ == "__init__":
        check_init_params(reference_params, compare_params)
        return

    for ref, cmp in itertools.zip_longest(reference_params, compare_params):
        if ref != cmp:
            raise _exceptions.APIImplementationError(
                "{}: expected parameter '{}', found '{}'".format(
                    reference.__name__, ref, cmp
                )
            )


class APIMeta(type):
    """Metaclass for an API implementation. All public methods must be a
    specified api method, but all api methods do not need to be implemented.
    """

    def __new__(mcs, name, bases, attrdict):
        api_methods = methods(APISpec.__dict__)
        implemented_methods = methods(attrdict)
        non_api_methods = set(implemented_methods.keys()) - set(
            api_methods.keys()
        )
        if non_api_methods:
            raise _exceptions.APIImplementationError(
                "non-API methods may not be public: {}".format(non_api_methods)
            )
        for method_name, method in api_methods.items():
            if method_name in implemented_methods:
                check_parameters(method, implemented_methods[method_name])
        return super().__new__(mcs, name, bases, attrdict)


class API(APISpec, metaclass=APIMeta):
    """API base class that all API implementations should inherit from. This
    class functions similarly to an abstract base class, but with a few key
    distinctions that affect the inheriting class.

    1. Public methods *must* override one of the public methods of
       :py:class:`APISpec`. If an inheriting class defines any other public
       method, an :py:class:`~repobee_plug.APIError` is raised when the
       class is defined.
    2. All public methods in :py:class:`APISpec` have a default implementation
       that simply raise a :py:class:`NotImplementedError`. There is no
       requirement to implement any of them.
    """
