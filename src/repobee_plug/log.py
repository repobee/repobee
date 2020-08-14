"""Logging functions."""

import logging

import daiquiri  # type: ignore

_LOG = daiquiri.getLogger(__file__)


def log(msg: str, level: int) -> None:
    """Log a message with a specific logging level.

    Args:
        msg: A message to log.
        level: The logging level.
    """
    _LOG.log(msg=msg, level=level)


def debug(msg: str) -> None:
    """Equivalent to ``log(msg, level=logging.DEBUG)``.

    Args:
        msg: A message to log.
    """
    log(msg, level=logging.DEBUG)


def info(msg: str) -> None:
    """Equivalent to ``log(msg, level=logging.INFO)``.

    Args:
        msg: A message to log.
    """
    log(msg, level=logging.INFO)


def warning(msg: str) -> None:
    """Equivalent to ``log(msg, level=logging.WARNING)``.

    Args:
        msg: A message to log.
    """
    log(msg, level=logging.WARNING)


def error(msg: str) -> None:
    """Equivalent to ``log(msg, level=logging.ERROR)``.

    Args:
        msg: A message to log.
    """
    log(msg, level=logging.ERROR)


def exception(msg: str) -> None:
    """Log an exception.

    Args:
        msg: A message to log.
    """
    _LOG.exception(msg)
