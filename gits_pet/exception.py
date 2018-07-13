"""Modules for all custom gits_pet exceptions."""
import os
import sys


class ParseError(Exception):
    """Raise when something goes wrong in parsing."""


class FileError(IOError):
    """Raise when reading or writing to a file errors out."""


class GitHubError(Exception):
    """An exception raised when the API responds with an error code."""

    def __init__(self, msg=None, status=None):
        self.status = status
        super().__init__(self, msg)


class NotFoundError(GitHubError):
    """An exception raised when the API responds with a 404."""


class UnexpectedException(GitHubError):
    """An exception raised when an API request raises an unexpected exception."""


class APIError(Exception):
    """Raise when something unexpected happens when interacting with the API."""


class GitError(Exception):
    """A generic error to raise when a git command exits with a non-zero
    exit status.
    """

    def __init__(self, msg: str, returncode: int, stderr: bytes):
        msg_ = ("{}{}"
                "return code: {}{}"
                "stderr: {}").format(
                    msg,
                    os.linesep,
                    returncode,
                    os.linesep,
                    stderr.decode(encoding=sys.getdefaultencoding()))
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(msg_)


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
