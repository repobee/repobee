"""Custom type definitions for use in type hints."""
from typing import TypeVar, Iterator

from typing_extensions import Protocol

T_co = TypeVar("T_co", covariant=True)


class SizedIterable(Protocol[T_co]):
    def __len__(self) -> int:
        ...

    def __iter__(self) -> Iterator[T_co]:
        ...
