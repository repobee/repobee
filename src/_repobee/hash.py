"""Utility functions for hashing."""
from typing import Any, Optional

import hashlib


def salted_hash(
    obj: Any, salt: Any, max_hash_size: Optional[int] = None
) -> str:
    """Return the hexdigest of a sha256 hash of the string representation of
    the input object, salted with the giiven salt and truncated to the given
    hash size.

    .. danger::

        This function is not made to be cryptographically secure, don't use it
        for anything where security is paramount.

    Args:
        obj: Any object to calculate a hash for.
        salt: A salt, typically a string.
        max_hash_size: The maximum size of the returned hash.
    Returns:
        A hash as described.
    """
    return hashlib.sha256((str(obj) + salt).encode("utf8")).hexdigest()[
        :max_hash_size
    ]
