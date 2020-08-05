"""IO functionality for plugins."""

import daiquiri

_LOG = daiquiri.getLogger(__file__)


def echo(msg: str) -> None:
    """Echo a message to the command line.

    Args:
        msg: The message to echo.
    """
    print(msg)
