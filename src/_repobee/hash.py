"""Utility functions for hashing."""
from typing import Any, Optional

import hashlib


def hash(obj: Any, max_hash_size: Optional[int] = None) -> str:
    """Return the hexdigest of a sha256 hash of the string representation of
    the input object, keyed with the giiven key and truncated to the given
    hash size.

    Args:
        obj: Any object to hash.
        max_hash_size: Maximum size of the returned hash.
    Returns:
        A hash.
    """
    return hashlib.sha256(str(obj).encode("utf8")).hexdigest()[:max_hash_size]


def keyed_hash(obj: Any, key: Any, max_hash_size: Optional[int] = None) -> str:
    """Return the hexdigest of a sha256 hash of the string representation of
    the input object, keyed with the giiven key and truncated to the given
    hash size.

    .. danger::

        This function is not made to be cryptographically secure, don't use it
        for anything where security is paramount.

    Args:
        obj: Any object to calculate a hash for.
        key: A key, typically a string.
        max_hash_size: The maximum size of the returned hash.
    Returns:
        A hash as described.
    """
    return hash(str(obj) + key, max_hash_size=max_hash_size)
