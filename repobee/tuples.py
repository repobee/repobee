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

Review = namedtuple("Review", ["repo", "done"])

Deprecation = namedtuple("Deprecation", ["replacement", "remove_by"])
