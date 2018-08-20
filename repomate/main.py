"""Main entrypoint for the repomate CLI application.

.. module:: main
    :synopsis: Main entrypoint for the repomate CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
import daiquiri

from repomate import cli
from repomate import exception

LOGGER = daiquiri.getLogger(__file__)


# if the OAUTH token is not set, OSError is raised
def main():
    """Start the repomate CLI."""
    try:
        parsed_args, api = cli.parse_args(sys.argv[1:])
        cli.dispatch_command(parsed_args, api)
    except Exception as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main()
