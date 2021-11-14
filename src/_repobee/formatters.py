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
from _repobee.colors import RESET, BackgroundColor, ForegroundColor

_STATUS_BACKGROUND_COLORS = {
    plug.Status.ERROR: BackgroundColor.RED,
    plug.Status.WARNING: BackgroundColor.YELLOW,
    plug.Status.SUCCESS: BackgroundColor.DARK_GREEN,
}


def format_peer_review_progress_output(
    reviews: Mapping[str, List[plug.Review]],
    teams: List[str],
    num_reviews: int,
):
    # can't use tabs for spacing as they are not background colored in output
    # for some reason each column should be exactly 16 characters
    output = [
        "Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews",  # noqa: E501
        RESET
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

    row = _format_row(
        [
            reviewer,
            num_performed_reviews,
            num_remaining_reviews,
            ",".join(remaining_reviews),
        ]
    )
    color = _compute_reviewer_row_color(review_progress, is_even_row=even)

    return f"{color}{row}{RESET}"


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


def _compute_reviewer_row_color(
    review_progress: _ReviewProgress, is_even_row: bool
) -> str:
    background_colors = {
        _ReviewProgress.DONE: BackgroundColor.DARK_GREEN,
        _ReviewProgress.NOT_DONE: BackgroundColor.LIGHT_GREY
        if is_even_row
        else BackgroundColor.DARK_GREY,
        _ReviewProgress.UNEXPECTED_AMOUNT_OF_REVIEWS: BackgroundColor.RED,
    }

    background_color = background_colors[review_progress]
    return f"{background_color}{ForegroundColor.WHITE}"


def format_hook_results_output(result_mapping):
    lines = []

    for repo_name, results in result_mapping.items():
        lines.append(
            f"{BackgroundColor.DARK_GREY}hook results for {repo_name}{RESET}"
        )
        _append_empty_lines(lines, 2)
        lines.extend(
            [f"{_format_hook_result(res)}{os.linesep}" for res in results]
        )
        _append_empty_lines(lines, 2)

    return "\n".join(lines)


def _append_empty_lines(lines, num_empty_lines):
    for _ in range(num_empty_lines):
        lines.append("")


def _format_hook_result(hook_result):
    bg_color = _STATUS_BACKGROUND_COLORS[hook_result.status]
    return (
        f"{bg_color}{ForegroundColor.WHITE}{hook_result.name}: "
        f"{hook_result.status.name}{RESET}\n{hook_result.msg}"
    )
