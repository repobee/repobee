"""Some general utility functions.

.. module:: util
    :synopsis: Miscellaneous utility functions that don't really belong
        anywhere else.

.. moduleauthor:: Simon Larsén
"""
from typing import Callable, TypeVar

T = TypeVar("T")


def repo_name(repo_url: str) -> str:
    """Extract the name of the repo from its url.

    Args:
        repo_url: A url to a repo.
    """
    repo_name = repo_url.split("/")[-1]
    if repo_name.endswith(".git"):
        return repo_name[:-4]
    return repo_name


def call_if_defined(func: Callable[..., T], *args, **kwargs) -> T:
    """Call the function with the provided args and kwargs if it is defined
    (i.e. not None). This is mostly useful for plugin data structures that have
    optional functions.

    Args:
        func: A function to call.
        args: Positional arguments.
        kwargs: Keyword arguments.
    Returns:
        What ``func`` returns, or ``None`` if ``func`` is ``None``.
    """
    return None if func is None else func(*args, **kwargs)
