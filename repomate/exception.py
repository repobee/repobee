"""Modules for all custom repomate exceptions.

All exceptions extend the :py:class:`RepomateException` base class, which itself
extends :py:class:`Exception`. In other words, exceptions raised within
``repomate`` can all be caught by catching :py:class:`RepomateException`.

.. module:: exception
    :synopsis: Custom exceptions for repomate.

.. moduleauthor:: Simon Larsén
"""
import os
import sys
import re


class RepomateException(Exception):
    """Base exception for all repomate exceptions."""

    def __init__(self, msg="", *args, **kwargs):
        super().__init__(self, msg, *args, **kwargs)
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return "<{}(msg='{}')>".format(type(self).__name__, str(self.msg))


class ParseError(RepomateException):
    """Raise when something goes wrong in parsing."""


class FileError(RepomateException):
    """Raise when reading or writing to a file errors out."""


class GitHubError(RepomateException):
    """An exception raised when the API responds with an error code."""

    def __init__(self, msg="", status=None):
        super().__init__(msg)
        self.status = status


class NotFoundError(GitHubError):
    """An exception raised when the API responds with a 404."""


class ServiceNotFoundError(GitHubError):
    """Raise if the base url can't be located."""


class BadCredentials(GitHubError):
    """Raise when credentials are rejected."""


class UnexpectedException(GitHubError):
    """An exception raised when an API request raises an unexpected exception."""


class APIError(RepomateException):
    """Raise when something unexpected happens when interacting with the API."""


class GitError(RepomateException):
    """A generic error to raise when a git command exits with a non-zero
    exit status.
    """

    def __init__(self, msg: str, returncode: int, stderr: bytes):
        stderr_decoded = stderr.decode(encoding=sys.getdefaultencoding()) or ''
        fatal = re.findall('fatal:.*', stderr_decoded)
        # either fatal reason or first line of error message
        err = fatal[0] if fatal else stderr_decoded.split(os.linesep)[0]

        # sanitize from secure token
        err = re.sub("https://.*?@", "https://", err)

        msg_ = ("{}{}return code: {}{}{}").format(msg, os.linesep, returncode,
                                                  os.linesep, err)
        super().__init__(msg_)
        self.returncode = returncode
        self.stderr = stderr


class CloneFailedError(GitError):
    """An error to raise when cloning a repository fails."""

    def __init__(self, msg: str, returncode: int, stderr: bytes, url: str):
        self.url = url
        super().__init__(msg, returncode, stderr)


class PushFailedError(GitError):
    """An error to raise when pushing to a remote fails."""

    def __init__(self, msg: str, returncode: int, stderr: bytes, url: str):
        self.url = url
        super().__init__(msg, returncode, stderr)


class PluginError(RepomateException):
    """Generic error to raise when something goes wrong with loading plugins."""
