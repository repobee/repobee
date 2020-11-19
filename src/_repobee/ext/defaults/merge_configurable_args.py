"""Hookwrapper that merges results from get_configurable_args such that there
are no duplicates in the otuput.
"""
import collections

import repobee_plug as plug
from repobee_plug.cli import args


@plug.repobee_hook(hookwrapper=True)
def get_configurable_args():
    """Merge configurable args by section and ensure that there are no
    duplicated argument names for a given section.
    """
    outcome = yield
    args_by_section = collections.defaultdict(list)
    for configurable_args in outcome.get_result():
        argnames = args_by_section[configurable_args.config_section_name]
        argnames.extend(
            [
                name
                for name in configurable_args.argnames
                if name not in argnames
            ]
        )

    outcome.force_result(
        [
            args.ConfigurableArguments(
                config_section_name=config_section_name, argnames=argnames
            )
            for config_section_name, argnames in args_by_section.items()
        ]
    )
