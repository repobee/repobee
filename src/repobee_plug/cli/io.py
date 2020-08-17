"""IO functionality for plugins."""

from typing import Iterable
from typing import TypeVar

import tqdm  # type: ignore

from repobee_plug import log

__all__ = [
    "echo",
    "progress_bar",
]

T = TypeVar("T")


def echo(msg: str) -> None:
    """Echo a message to the command line.

    Args:
        msg: The message to echo.
    """
    log.info(msg)
    print(msg)


def progress_bar(it: Iterable[T], *args, **kwargs) -> Iterable[T]:
    """Create a progress bar for an iterable.

    .. danger::

        The API of this function is not stable and may change unexpectedly.

    Args:
        it: An iterable.
        args: Positional arguments passed directly to the underlying
            implementation (currently `tqdm`).
        kwargs: Keyword arguments passed directly to the underlying
            implementation (currently `tqdm`).
    Returns:
        An iterable object that returns elements from ``it``, and also updates
        a progress bar in the terminal.
    """
    return tqdm.tqdm(it, *args, **kwargs)
