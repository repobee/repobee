"""Tuples module.

This module contains various namedtuple containers used throughout repobee.
There are still a few namedtuples floating about in their own modules, but
the goal is to collect all container types in this module.

.. module:: tuples
    :synopsis: Module containing various namedtuple containers used throughout
        repobee.

.. moduleauthor:: Simon Larsén
"""
from collections import namedtuple

import daiquiri

LOGGER = daiquiri.getLogger(__file__)


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


class Issue(
    namedtuple("Issue", ("title", "body", "number", "created_at", "author"))
):
    def __new__(cls, title, body, number=None, created_at=None, author=None):
        return super().__new__(cls, title, body, number, created_at, author)


class Group(namedtuple("Group", ("members"))):
    # GitHub allows only 100 characters for repository names
    MAX_STR_LEN = 100

    def __str__(self):
        return "-".join(sorted(self.members))

    def __new__(cls, members):
        instance = super().__new__(cls, members)
        team_name = Group.__str__(instance)
        _check_name_length(team_name)
        return instance


Args = namedtuple(
    "Args",
    (
        "subparser",
        "org_name",
        "github_base_url",
        "user",
        "master_repo_urls",
        "master_repo_names",
        "students",
        "issue",
        "title_regex",
        "traceback",
        "state",
        "show_body",
        "author",
        "num_reviews",
        "master_org_name",
        "token",
    ),
)
Args.__new__.__defaults__ = (None,) * len(Args._fields)

Team = namedtuple("Team", ("name", "members", "id"))


class Repo(
    namedtuple("Repo", ("name", "description", "private", "team_id", "url"))
):
    def __new__(cls, name, description, private, team_id=None, url=None):
        _check_name_length(name)
        return super().__new__(cls, name, description, private, team_id, url)


Review = namedtuple("Review", ["repo", "done"])

Deprecation = namedtuple("Deprecation", ["replacement", "remove_by"])
