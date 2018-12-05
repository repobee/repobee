"""Output formatting functions for top-level commands.

This module contains functions for pretty formatting of command line output.

.. module:: command
    :synopsis: Functions for pretty formatting of command line output.

.. moduleauthor:: Simon Larsén
"""
import os
from typing import Mapping, List

from colored import fg, bg, style
from repomate_plug import Status
import daiquiri

from repomate import tuples

LOGGER = daiquiri.getLogger(__name__)


def format_peer_review_progress_output(
        reviews: Mapping[str, List[tuples.Review]], students: List[str],
        num_reviews: int):
    # can't use tabs for spacing as they are not background colored in output for some reason
    # each column should be exactly 16 characters
    output = [
        "Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews",
        style.RESET + _format_row(
            ["reviewer", "num done", "num remaining", "repos remaining"])
    ]
    even = False
    for reviewer in students:
        even = not even
        review_list = reviews[reviewer]
        output.append(
            _format_reviewer(reviewer, review_list, students, num_reviews,
                             even))
    return os.linesep.join(output)


def _format_row(items: List[str]) -> str:
    column_width = 16
    return "".join([str(item).ljust(column_width) for item in items])


def _format_reviewer(reviewer: str, review_list: List[tuples.Review],
                     students: List[str], num_reviews: bool, even: bool):
    performed_reviews = [rev.repo for rev in review_list if rev.done]
    remaining_reviews = [rev.repo for rev in review_list if not rev.done]
    color = (bg('grey_30') if even else bg('grey_15'))

    if len(performed_reviews) == num_reviews and not remaining_reviews:
        color = bg('dark_green')
    elif len(review_list) != num_reviews:
        LOGGER.warning(
            ("expected {} to be assigned to {} review teams, but found {}. "
             "Review teams may have been tampered with.").format(
                 reviewer, num_reviews, len(review_list)))
        color = bg('red')
    color += fg('white')

    return color + _format_row([
        reviewer,
        len(performed_reviews),
        len(remaining_reviews), ",".join(remaining_reviews)
    ]) + style.RESET


def format_hook_result(hook_result):
    if hook_result.status == Status.ERROR:
        out = bg('red')
    elif hook_result.status == Status.WARNING:
        out = bg('yellow')
    elif hook_result.status == Status.SUCCESS:
        out = bg('dark_green')
    else:
        raise ValueError(
            "expected hook_result.status to be one of Status.ERROR, "
            "Status.WARNING or Status.SUCCESS, but was {!r}".format(
                hook_result.status))

    out += fg(
        'white'
    ) + hook_result.hook + ": " + hook_result.status.name + style.RESET + os.linesep
    out += hook_result.msg

    return out


def format_hook_results_output(result_mapping):
    out = ""
    for repo_name, results in result_mapping.items():
        out += "{}hook results for {}{}{}".format(
            bg('grey_23'), repo_name, style.RESET, os.linesep * 2)
        out += os.linesep.join([
            "{}{}".format(format_hook_result(res), os.linesep)
            for res in results
        ])
        out += os.linesep * 2

    return out
