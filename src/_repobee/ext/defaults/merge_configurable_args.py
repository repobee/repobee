"""Hookwrapper that merges results from get_configurable_args such that there
are no duplicates in the otuput.
"""
import collections
import itertools

from typing import Iterable, Mapping, List

import repobee_plug as plug
from repobee_plug.cli import args


@plug.repobee_hook(hookwrapper=True)
def get_configurable_args():
    """Merge configurable args by section and ensure that there are no
    duplicated argument names for a given section.
    """
    outcome = yield
    merged_arguments = _merge_args_by_section_name(outcome.get_result())
    outcome.force_result(list(merged_arguments))


def _merge_args_by_section_name(
    unmerged_configurable_args: Iterable[args.ConfigurableArguments],
) -> Iterable[args.ConfigurableArguments]:
    args_by_section_name = _get_unique_args_by_section_name(
        unmerged_configurable_args
    )
    return itertools.starmap(
        args.ConfigurableArguments, args_by_section_name.items()
    )


def _get_unique_args_by_section_name(
    unmerged_configurable_args: Iterable[args.ConfigurableArguments],
) -> Mapping[str, List[str]]:
    args_by_section: Mapping[str, List[str]] = collections.defaultdict(list)
    for configurable_args in unmerged_configurable_args:
        argnames = args_by_section[configurable_args.config_section_name]
        argnames.extend(
            [
                name
                for name in configurable_args.argnames
                if name not in argnames
            ]
        )

    return args_by_section
