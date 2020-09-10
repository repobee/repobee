"""IO functionality for plugins."""
import sys

from typing import Iterable, TypeVar, Any

import tqdm  # type: ignore

from repobee_plug import log

__all__ = [
    "echo",
    "progress_bar",
]

T = TypeVar("T")


def echo(msg: Any) -> None:
    """Echo a message to the command line.

    Args:
        msg: Any kind of object that can be converted into a human-readable
            string with the ``str`` function.
    """
    msg = str(msg)
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
    return tqdm.tqdm(it, *args, file=sys.stdout, **kwargs)
