import os
import sys
import pytest
from repomate import exception
from repomate import git

USER = pytest.constants.USER


def test_repomate_exception_repr():
    msg = "an exception message"
    expected_repr = "<RepomateException(msg='{}')>".format(msg)
    exc = exception.RepomateException(msg)

    assert repr(exc) == expected_repr


class TestGitError:
    """Tests for GitError."""

    def test_empty_values(self):
        """Test both that there are no crashes, and that values are stored
        correctly.
        """
        msg = ""
        stderr = b""
        returncode = 128

        err = exception.GitError(msg, returncode, stderr)

        assert err.returncode == returncode
        assert err.stderr == stderr

    def test_fatal_message_is_picked(self):
        """Test that the line with ``fatal:`` on it is picked for the
        message.
        """
        msg = "something something dark side"
        fatal = "fatal: this is the part we want!"
        stderr = "Some error stuff\n{}\nmore lines\nmore lines".format(
            fatal).encode(sys.getdefaultencoding())
        returncode = 128

        expected_msg = "{}{}return code: {}{}{}".format(
            msg, os.linesep, returncode, os.linesep, fatal)

        err = exception.GitError(msg, returncode, stderr)

        assert str(err) == expected_msg

    def test_token_is_sanitized_no_username(self):
        """Test that the token is sanitized when it's in the URL, but with no
        username (happens e.g. when pulling repos fails, as username must not
        be specified)
        """
        token = "032957238hfibwt8374"  # random garbage token
        returncode = 128
        repo_url = "{}/some-repo".format(pytest.constants.HOST_URL)
        repo_url_with_token = git._insert_token(repo_url, token)
        fatal = "fatal: repo '{}' could not be found".format(
            repo_url_with_token)
        assert token in fatal  # meta assert, make sure we are testing something
        msg = "something went wrong!"
        stderr = "some lines\n{}\nlast line".format(fatal).encode(
            sys.getdefaultencoding())
        expected_msg = "{}{}return code: {}{}{}".format(
            msg, os.linesep, returncode, os.linesep,
            "fatal: repo '{}' could not be found".format(repo_url))

        err = exception.GitError(msg, returncode, stderr)

        assert token not in str(err)
        assert str(err) == expected_msg

    def test_token_is_sanitized_with_username(self):
        """Test that the token is sanitized when it's in the URL along with a
        username (happens e.g. when pushing repos fails, as username must be
        specified)
        """
        token = "032957238hfibwt8374"  # random garbage token
        returncode = 128
        repo_url = "{}/some-repo".format(pytest.constants.HOST_URL)
        repo_url_with_user_and_token = git._insert_user_and_token(
            repo_url, USER, token)
        fatal = "fatal: repo '{}' could not be found".format(
            repo_url_with_user_and_token)
        assert token in fatal  # meta assert, make sure we are testing something
        assert USER in fatal
        msg = "something went wrong!"
        stderr = "some lines\n{}\nlast line".format(fatal).encode(
            sys.getdefaultencoding())
        expected_msg = "{}{}return code: {}{}{}".format(
            msg, os.linesep, returncode, os.linesep,
            "fatal: repo '{}' could not be found".format(repo_url))

        err = exception.GitError(msg, returncode, stderr)

        assert token not in str(err)
        assert USER not in str(err)
        assert str(err) == expected_msg
