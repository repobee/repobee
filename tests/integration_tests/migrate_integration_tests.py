"""Integration tests for the migrate command."""

import pytest

import _repobee.cli.mainparser

import asserts
from helpers import *


@pytest.mark.filterwarnings("ignore:.*Unverified HTTPS request.*")
class TestMigrate:
    """Integration tests for the migrate command."""

    @pytest.fixture
    def local_master_repos(self, restore, extra_args):
        """Clone the master repos to disk. The restore fixture is explicitly
        included as it must be run before this fixture.
        """
        api = api_instance(MASTER_ORG_NAME)
        master_repo_urls = [
            url.replace(LOCAL_DOMAIN, BASE_DOMAIN)
            for url in api.get_repo_urls(MASTER_REPO_NAMES)
        ]
        # clone the master repos to disk first first
        git_commands = ["git clone {}".format(url) for url in master_repo_urls]
        result = run_in_docker(
            " && ".join(git_commands), extra_args=extra_args
        )

        assert result.returncode == 0
        return MASTER_REPO_NAMES

    def test_happy_path(self, local_master_repos, extra_args, target_group_name, base_args):
        """Migrate a few repos from the existing master repo into the target
        organization.
        """
        command = " ".join(
            [
                REPOBEE_GITLAB,
                _repobee.cli.mainparser.MIGRATE_PARSER,
                *base_args,
                *MASTER_REPOS_ARG,
            ]
        )

        result = run_in_docker_with_coverage(command, extra_args=extra_args)

        assert result.returncode == 0
        asserts.assert_master_repos_exist(local_master_repos, target_group_name)
