"""Custom type definitions for use in type hints."""
from typing import TypeVar, Iterator

from typing_extensions import Protocol

T = TypeVar("T", covariant=True)


class SizedIterable(Protocol[T]):
    def __len__(self) -> int:
        ...

    def __iter__(self) -> Iterator[T]:
        ...
