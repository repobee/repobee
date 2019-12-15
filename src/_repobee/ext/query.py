"""A plugin that adds the ``query`` command to RepoBee, allowing users to query
a hook results JSON file.

.. module:: query
    :synopsis: Plugin that adds a query command to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
import sys
import collections

import daiquiri
import repobee_plug as plug

from _repobee import formatters

LOGGER = daiquiri.getLogger(__file__)


def callback(args: argparse.Namespace, api: plug.API) -> None:
    hook_results_file = pathlib.Path(args.hook_results_file).resolve()
    if not hook_results_file.exists():
        raise plug.PlugError("no such file: {}".format(str(hook_results_file)))

    contents = hook_results_file.read_text(encoding=sys.getdefaultencoding())
    hook_results_mapping = plug.json_to_result_mapping(contents)
    selected_hook_results = _filter_hook_results(
        hook_results_mapping, args.students, args.master_repo_names
    )
    LOGGER.info(formatters.format_hook_results_output(selected_hook_results))


@plug.repobee_hook
def create_extension_command():
    LOGGER.warning(
        "query is an experimental plugin and may be altered or removed "
        "without notice."
    )
    parser = plug.ExtensionParser()
    parser.add_argument(
        "--hf",
        "--hook-results-file",
        help="Path to an existing hook results file.",
        type=str,
        required=True,
        dest="hook_results_file",
    )
    return plug.ExtensionCommand(
        parser=parser,
        name="query",
        help="Query a hook results JSON file for information.",
        description="Query a hook results JSON file for information.",
        callback=callback,
        requires_base_parsers=[
            plug.BaseParser.STUDENTS,
            plug.BaseParser.REPO_NAMES,
        ],
    )


def _filter_hook_results(hook_results_mapping, teams, master_repo_names):
    """Return an OrderedDict of hook result mappings for which the repo name is
    contained in the cross product of teams and master repo names.
    """
    repo_names = set(plug.generate_repo_names(teams, master_repo_names))
    selected_hook_results = collections.OrderedDict()
    for repo_name, hook_results in sorted(hook_results_mapping.items()):
        if repo_name in repo_names:
            selected_hook_results[repo_name] = hook_results
    missing_repo_names = repo_names - selected_hook_results.keys()
    _log_missing_repo_names(missing_repo_names)
    return selected_hook_results


def _log_missing_repo_names(missing_repo_names):
    if missing_repo_names:
        LOGGER.warning(
            "No hook results found for {}".format(
                ", ".join(missing_repo_names)
            )
        )
