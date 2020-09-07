"""Immutable mixin class."""


class ImmutableMixin:
    """Make a class (more or less) immutable."""

    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__class__} is immutable")

    def __setattribute__(self, name, value):
        self.__setattr__(name, value)
