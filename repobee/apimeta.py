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

import daiquiri

from repobee import exception

LOGGER = daiquiri.getLogger(__file__)


class APIObject:
    """Base wrapper class for platform API objects."""


def _check_name_length(name):
    """Check that a Team/Repository name does not exceed the maximum GitHub
    allows (100 characters)
    """
    max_len = 100
    if len(name) > max_len:
        LOGGER.error("Team/Repository name {} is too long".format(name))
        raise ValueError(
            "generated Team/Repository name is too long, was {} chars, "
            "max is {} chars".format(len(name), max_len)
        )
    elif len(name) > max_len * 0.8:
        LOGGER.warning(
            "Team/Repository name {} is {} chars long, close to the max of "
            "{} chars.".format(name, len(name), max_len)
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

    def ensure_teams_and_members(self, member_lists, permission):
        _not_implemented()

    def get_teams(self):
        _not_implemented()

    def create_repos(self, repos):
        _not_implemented()

    def get_repo_urls(self, master_repo_names, org_name, students):
        _not_implemented()

    def get_issues(self, repo_names, state, title_regex):
        _not_implemented()

    def open_issue(self, title, body, repo_names):
        _not_implemented()

    def close_issue(self, title_regex, repo_names):
        _not_implemented()

    def add_repos_to_review_teams(self, team_to_repos, issue):
        _not_implemented()

    def get_review_progress(self, review_team_names, students, title_regex):
        _not_implemented()

    def delete_teams(self, team_names):
        _not_implemented()

    @staticmethod
    def verify_settings(user, org_name, base_url, token, master_org_name):
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
