"""Main entrypoint for the gits_pet CLI application.

.. module:: main
    :synopsis: Main entrypoint for the gits_pet CLI application.

.. moduleauthor:: Simon Larsén
"""

import sys
import daiquiri

from gits_pet import cli
from gits_pet import exception

LOGGER = daiquiri.getLogger(__file__)


# if the OAUTH token is not set, OSError is raised
def main():
    """Start the gits_pet CLI."""
    try:
        parsed_args, api = cli.parse_args(sys.argv[1:])
        cli.dispatch_command(parsed_args, api)
    except Exception as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main()
