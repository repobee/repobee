import sys
import os
import pytest
import subprocess
import string
from asyncio import coroutine
from unittest.mock import patch, PropertyMock, MagicMock
from collections import namedtuple

import gits_pet
from gits_pet import admin
from gits_pet import github_api

USER = 'slarse'
ORG_NAME = 'test-org'
GITHUB_BASE_API = 'https://some_enterprise_host/api/v3'


@pytest.fixture(autouse=True)
def git_mock(mocker):
    """Mocks the whole git module so that there are no accidental
    pushes/clones.
    """
    mocker.patch('gits_pet.git', autospec=True)


@pytest.fixture(autouse=True)
def api_mock(mocker):
    mocker.patch('gits_pet.admin.GitHubAPI', autospec=True)
    return api_mock


@pytest.fixture(scope='function')
def master_urls():
    master_urls = [
        'https://someurl.git', 'https://better_url.git',
        'https://another-url.git'
    ]
    return master_urls


@pytest.fixture(scope='function')
def students():
    return list(string.ascii_lowercase)


def test_create_multiple_student_repos_raises_on_duplicate_master_urls(
        master_urls, students):
    master_urls.append(master_urls[0])

    with pytest.raises(ValueError) as exc_info:
        admin.create_multiple_student_repos(master_urls, USER, students,
                                            ORG_NAME, GITHUB_BASE_API)
    assert str(exc_info.value) == "master_repo_urls contains duplicates"
