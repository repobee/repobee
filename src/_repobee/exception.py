"""Modules for all custom repobee exceptions.

All exceptions extend the :py:class:`RepoBeeException` base class, which
itself extends :py:class:`Exception`. In other words, exceptions raised within
``repobee`` can all be caught by catching :py:class:`RepoBeeException`.

.. module:: exception
    :synopsis: Custom exceptions for _repobee.

.. moduleauthor:: Simon Larsén
"""
import os
import sys
import re


class RepoBeeException(Exception):
    """Base exception for all repobee exceptions."""

    def __init__(self, msg="", *args, **kwargs):
        super().__init__(self, msg, *args, **kwargs)
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return "<{}(msg='{}')>".format(type(self).__name__, str(self.msg))


class ParseError(RepoBeeException):
    """Raise when something goes wrong in parsing."""


class FileError(RepoBeeException):
    """Raise when reading or writing to a file errors out."""


class GitError(RepoBeeException):
    """A generic error to raise when a git command exits with a non-zero exit
    status.
    """

    def __init__(self, msg: str, returncode: int, stderr: bytes):
        stderr_decoded = stderr.decode(encoding=sys.getdefaultencoding()) or ""
        fatal = re.findall("fatal:.*", stderr_decoded)
        # either fatal reason or first line of error message
        err = fatal[0] if fatal else stderr_decoded.split(os.linesep)[0]

        # sanitize from secure token
        err = re.sub("https://.*?@", "https://", err)

        msg_ = ("{}{}return code: {}{}{}").format(
            msg, os.linesep, returncode, os.linesep, err
        )
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


class PluginLoadError(RepoBeeException):
    """Generic error to raise when something goes wrong with loading
    plugins.
    """
