"""Output formatting functions for top-level commands.

This module contains functions for pretty formatting of command line output.

.. module:: command
    :synopsis: Functions for pretty formatting of command line output.

.. moduleauthor:: Simon Larsén
"""
import os
import enum
from typing import Mapping, List, Any

import repobee_plug as plug

_RED = "\x1b[48;5;1m"
_YELLOW = "\x1b[48;5;3m"
_DARK_GREEN = "\x1b[48;5;22m"
_LIGHT_GREY = "\x1b[48;5;235m"
_DARK_GREY = "\x1b[48;5;239m"
_WHITE = "\x1b[38;5;15m"
_RESET = "\x1b[0m"


def format_peer_review_progress_output(
    reviews: Mapping[str, List[plug.Review]],
    teams: List[str],
    num_reviews: int,
):
    # can't use tabs for spacing as they are not background colored in output
    # for some reason each column should be exactly 16 characters
    output = [
        "Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews",  # noqa: E501
        _RESET
        + _format_row(
            ["reviewer", "num done", "num remaining", "repos remaining"]
        ),
    ]
    even = False
    for review_team in teams:
        even = not even
        review_list = reviews[str(review_team)]
        output.append(
            _format_reviewer(review_team, review_list, num_reviews, even)
        )
    return os.linesep.join(output)


def _format_row(items: List[Any]) -> str:
    column_width = 16
    return "".join([str(item).ljust(column_width) for item in items])


def _format_reviewer(
    reviewer: str,
    review_list: List[plug.Review],
    num_reviews: int,
    even: bool,
):
    num_performed_reviews = len([rev.repo for rev in review_list if rev.done])
    remaining_reviews = [rev.repo for rev in review_list if not rev.done]
    num_remaining_reviews = len(remaining_reviews)

    background_colors = {
        _ReviewProgress.DONE: _DARK_GREEN,
        _ReviewProgress.NOT_DONE: _DARK_GREY if even else _LIGHT_GREY,
        _ReviewProgress.UNEXPECTED_AMOUNT_OF_REVIEWS: _RED,
    }

    review_progress = _compute_review_progress(
        num_performed_reviews,
        num_remaining_reviews,
        num_expected_reviews=num_reviews,
    )

    if review_progress == _ReviewProgress.UNEXPECTED_AMOUNT_OF_REVIEWS:
        plug.log.warning(
            f"Expected {reviewer} to be assigned to {num_reviews} review "
            f"teams, but found {len(review_list)}. "
            f"Review teams may have been tampered with."
        )

    background_color = background_colors[review_progress]
    foreground_color = _WHITE
    color = f"{background_color}{foreground_color}"

    row = _format_row(
        [
            reviewer,
            num_performed_reviews,
            num_remaining_reviews,
            ",".join(remaining_reviews),
        ]
    )

    formatted_row = f"{color}{row}{_RESET}"
    plug.log.warning(formatted_row.encode("utf8"))

    return formatted_row


class _ReviewProgress(enum.Enum):
    DONE = enum.auto()
    NOT_DONE = enum.auto()
    UNEXPECTED_AMOUNT_OF_REVIEWS = enum.auto()


def _compute_review_progress(
    num_performed_reviews: int,
    num_remaining_reviews: int,
    num_expected_reviews: int,
) -> _ReviewProgress:
    if num_performed_reviews + num_remaining_reviews != num_expected_reviews:
        return _ReviewProgress.UNEXPECTED_AMOUNT_OF_REVIEWS
    elif num_performed_reviews == num_expected_reviews:
        return _ReviewProgress.DONE
    else:
        return _ReviewProgress.NOT_DONE


def format_hook_result(hook_result):
    if hook_result.status == plug.Status.ERROR:
        out = _RED
    elif hook_result.status == plug.Status.WARNING:
        out = _YELLOW
    elif hook_result.status == plug.Status.SUCCESS:
        out = _DARK_GREEN
    else:
        raise ValueError(
            f"expected hook_result.status to be one of Status.ERROR, "
            f"Status.WARNING or Status.SUCCESS, but was {hook_result.status}"
        )

    out += (
        _WHITE
        + hook_result.name
        + ": "
        + hook_result.status.name
        + _RESET
        + os.linesep
    )
    out += hook_result.msg

    return out


def format_hook_results_output(result_mapping):
    out = ""
    for repo_name, results in result_mapping.items():
        out += (
            f"{_DARK_GREY}hook results for {repo_name}{_RESET}{os.linesep * 2}"
        )
        out += os.linesep.join(
            [f"{format_hook_result(res)}{os.linesep}" for res in results]
        )
        out += os.linesep * 2

    return out
