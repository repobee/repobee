"""A plugin that adds the ``query`` command to RepoBee, allowing users to query
a hook results JSON file for data.

.. module:: query
    :synopsis: Plugin that adds a configuration wizard to RepoBee.

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
import sys
import json

import daiquiri
import repobee_plug as plug

from repobee_plug import apimeta

from _repobee import formatters

LOGGER = daiquiri.getLogger(__file__)


def callback(args: argparse.Namespace, api: apimeta.API) -> None:
    hook_results_file = pathlib.Path(args.hook_results_file).resolve()
    if not hook_results_file.exists():
        raise plug.PlugError("no such file: {}".format(str(hook_results_file)))
    contents = hook_results_file.read_text(encoding=sys.getdefaultencoding())
    hook_results_mapping = plug.json_to_result_mapping(contents)
    repo_names = set(
        plug.generate_repo_names(args.students, args.master_repo_names)
    )
    selected_hook_results = {
        repo_name: hook_results
        for repo_name, hook_results in hook_results_mapping.items()
        if repo_name in repo_names
    }
    missing_repo_names = repo_names - selected_hook_results.keys()
    if missing_repo_names:
        LOGGER.warning(
            "No hook results found for {}".format(
                ", ".join(missing_repo_names)
            )
        )
    if not args.hook:
        LOGGER.info(
            formatters.format_hook_results_output(selected_hook_results)
        )
    else:
        for repo_name, hook_results in selected_hook_results.items():
            specific_results = [
                res for res in hook_results if res.hook == args.hook
            ]
            if not specific_results:
                LOGGER.warning(
                    "{} has no result for hook {}".format(repo_name, args.hook)
                )

            for result in specific_results:
                if not args.query:
                    LOGGER.info(
                        "{}.{}:\n{}".format(
                            repo_name,
                            args.hook,
                            json.dumps(result.data, indent=4),
                        )
                    )
                else:
                    try:
                        queried_data = resolve_query(result.data, args.query)
                        msg = "{}.{}.{}:\n{}".format(
                            repo_name,
                            args.hook,
                            ".".join(args.query),
                            "\n".join(
                                [
                                    "QUERY_PATH={}\n{}".format(
                                        ".".join(path), data
                                    )
                                    for path, data in queried_data
                                ]
                            ),
                        )
                        LOGGER.info(msg)
                    except KeyError:
                        LOGGER.warning(
                            "cannot resolve query for {}".format(repo_name)
                        )


def resolve_query(data, query_keys, path=None):
    """Inefficient but simple querying. Does NOT scale."""
    path = path or []
    active_key, *rest = query_keys
    try:
        current_data = data[active_key]
        path.append(active_key)
    except KeyError:
        results = []
        for k, v in data.items():
            if isinstance(v, dict):
                res = resolve_query(v, query_keys, path + [k])
                results += res
        return results

    if not rest:
        return [(path, current_data)]
    return resolve_query(current_data, rest, list(path))


@plug.repobee_hook
def create_extension_command():
    parser = plug.ExtensionParser()
    parser.add_argument(
        "--hf",
        "--hook-results-file",
        help="Path to an existing hook results file.",
        type=str,
        required=True,
        dest="hook_results_file",
    )
    parser.add_argument(
        "--hook",
        help="Return the data segment for this specific hook. Use "
        "`--query` to get specific data from the data segment.",
    )
    parser.add_argument(
        "-q",
        "--query",
        help="Query the 'data' segment of a hook result with one or more "
        "space-separated keys. Requires that a hook is specified with the "
        "--hook option.",
        type=str,
        nargs="+",
        default=None,
    )
    return plug.ExtensionCommand(
        parser=parser,
        name="query",
        help="Query a hook results JSON file for information.",
        description=("Query a hook results JSON file for information."),
        callback=callback,
        requires_base_parsers=[
            plug.BaseParser.STUDENTS,
            plug.BaseParser.REPO_NAMES,
        ],
    )
