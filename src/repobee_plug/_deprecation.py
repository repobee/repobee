"""Module with functions for dealing with deprecation.

.. module:: _deprecation
    :synopsis: Module with functions for dealing with deprecation.
"""
from typing import Optional, Mapping, Callable, Any, TypeVar
from repobee_plug import _containers
from repobee_plug import exceptions

AnyFunction = Callable[..., Any]

T = TypeVar("T")


def deprecate(
    remove_by_version: str, replacement: Optional[str] = None
) -> Callable[[T], T]:
    """Return a function that can be used to deprecate functions. Currently
    this is only used for deprecation of hook functions, but it may be expanded
    to deprecated other things in the future.

    Args:
        remove_by_version: A string that should contain a version number.
        replacement: An optional string with the name of the replacing
            function.
    Returns:
        A function

    """
    dep = _containers.Deprecation(
        replacement=replacement, remove_by_version=remove_by_version
    )

    def _inner(func):
        if "repobee_plug_spec" not in dir(func):
            raise exceptions.PlugError(
                "can't deprecate non-hook function", func=func
            )
        deprs = _Deprecations()
        deprs.deprecate_hook(func.__name__, dep)
        return func

    return _inner


def deprecated_hooks() -> Mapping[str, _containers.Deprecation]:
    """
    Returns:
        A mapping of hook names to :py:class:`~containers.Deprecation` tuples.
    """
    return dict(_Deprecations().deprecated_hooks)


class _Deprecations:
    """Class for keeping track of deprecated functionality. This class is
    singleton and is meant to be accessed by using its constructor. That is to
    say, every call to ``Deprecations()`` will return the same instance, only
    the first call will actually instantiate a new instance.
    """

    _instance = None
    deprecated_hooks: dict

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst.deprecated_hooks = {}
            cls._instance = inst
        return cls._instance

    def deprecate_hook(
        self, hook_name: str, deprecation: _containers.Deprecation
    ) -> None:
        """Deprecate a hook function with the given name.

        Args:
            hook_name: Name of the hook to deprecate.
            deprecation: A Deprecation tuple.
        """
        self.deprecated_hooks[hook_name] = deprecation
