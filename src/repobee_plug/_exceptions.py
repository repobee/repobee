"""Exceptions for repobee_plug.

.. module:: exception
    :synopsis: Exceptions for repobee_plug.

.. moduleauthor:: Simon Larsén
"""


class PlugError(Exception):
    """Base class for all repobee_plug exceptions."""

    def __init__(self, *args, **kwargs):
        """Instantiate a PlugError.

        Args:
            args: List of positionals. These are passed directly to
                :py:class:`Exception`. Typically, you should only
                pass an error message here.
            kwargs: Keyword arguments to indicate what went wrong.
                For example, if the argument ``a`` caused the error, then you
                should pass ``a=a`` as a kwarg so it can be introspected at a
                later time.
        """
        super().__init__(*args)
        self._kwargs = kwargs

    @property
    def kwargs(self):
        return dict(self._kwargs)

    def __str__(self):
        formatted_args = super().__str__()
        formatted_kwargs = (
            ""
            if not self._kwargs
            else ". Passed arguments: "
            + ", ".join(
                "{}={}".format(key, value)
                for key, value in self._kwargs.items()
            )
        )
        return "{}{}".format(formatted_args, formatted_kwargs)


class HookNameError(PlugError):
    """Raise when a public method in a class that inherits from
    :py:class:`~repobee_plug.Plugin` does not have a hook name.
    """


class ExtensionCommandError(PlugError):
    """Raise when an :py:class:~repobee_plug.containers.ExtensionCommand: is
    incorrectly defined.
    """


class APIImplementationError(PlugError):
    """Raise when an API is defined incorrectly."""
