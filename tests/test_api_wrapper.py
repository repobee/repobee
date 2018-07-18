from unittest.mock import MagicMock, PropertyMock
from collections import namedtuple
import pytest
import github

from gits_pet import api_wrapper
from gits_pet import git
from gits_pet import exception

USER = pytest.constants.USER
NOT_OWNER = 'notanowner'
ORG_NAME = pytest.constants.ORG_NAME
GITHUB_BASE_URL = pytest.constants.GITHUB_BASE_URL

User = namedtuple('User', ('login', ))


class GithubException(Exception):
    def __init__(self, msg, status):
        self.msg = msg
        self.status = status


def raise_404(*args, **kwargs):
    raise GithubException("Couldn't find something", 404)


@pytest.fixture
def happy_github(mocker):
    """mock of github.Github which raises no exceptions and returns the
    correct values.
    """
    # github module is mocked in conftest
    github.GithubException = GithubException

    organization = MagicMock()
    organization.get_members = lambda role: \
        [User(login='blablabla'), User(login='hello'), User(login=USER)]
    github_instance = MagicMock()
    github_instance.get_user.side_effect = \
        lambda user: User(login=user) if user in [USER, NOT_OWNER] else raise_404()
    github_instance.get_organization.side_effect = \
        lambda org_name: organization if org_name == ORG_NAME else raise_404()
    type(github_instance).oauth_scopes = PropertyMock(
        return_value=api_wrapper.REQUIRED_OAUTH_SCOPES)

    github.Github.side_effect = lambda login_or_token, base_url: github_instance
    return github_instance


@pytest.fixture(params=['get_user', 'get_organization'])
def github_bad_info(request, happy_github):
    """Fixture with a github instance that raises GithubException 404 when
    use the user, base_url and org_name arguments to .
    """
    getattr(happy_github, request.param).side_effect = raise_404


class TestVerifyConnection:
    """Tests for the verify_connection function."""

    def test_happy_path(self, happy_github):
        """Tests that no exceptions are raised when all info is correct."""
        api_wrapper.verify_connection(USER, ORG_NAME, git.OAUTH_TOKEN,
                                      GITHUB_BASE_URL)

    def test_incorrect_info_raises_not_found_error(self, github_bad_info):
        with pytest.raises(exception.NotFoundError) as exc_info:
            api_wrapper.verify_connection(USER, ORG_NAME, git.OAUTH_TOKEN,
                                          GITHUB_BASE_URL)

    def test_bad_token_scope_raises(self, happy_github):
        type(happy_github).oauth_scopes = PropertyMock(return_value=['repo'])

        with pytest.raises(exception.BadCredentials) as exc_info:
            api_wrapper.verify_connection(USER, ORG_NAME, git.OAUTH_TOKEN,
                                          GITHUB_BASE_URL)
        assert "missing one or more oauth scopes" in str(exc_info)

    def test_not_owner_raises(self, happy_github):
        with pytest.raises(exception.BadCredentials) as exc_info:
            api_wrapper.verify_connection(NOT_OWNER, ORG_NAME, git.OAUTH_TOKEN,
                                          GITHUB_BASE_URL)

        assert "user {} is not an owner".format(NOT_OWNER) in str(exc_info)
