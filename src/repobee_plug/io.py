"""IO functionality for plugins."""

import daiquiri
import logging

_LOG = daiquiri.getLogger(__file__)


def echo(msg: str) -> None:
    """Echo a message to the command line.

    Args:
        msg: The message to echo.
    """
    print(msg)


def log(msg: str, level: int = logging.INFO) -> None:
    """Log a message with a specific logging level.

    Args:
        msg: A message to loggin.
        level: The logging level.
    """
    _LOG.log(msg, level=level)
