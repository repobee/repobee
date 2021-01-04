import re
import itertools

import git

import repobee_plug as plug

from repobee_testhelpers._internal.docker import run_in_docker_with_coverage
from repobee_testhelpers._internal import templates as template_helpers

import giteamanager


class TestSetup:
    def test_setup_once(self, extra_args, tmpdir):
        """Test that running setup once results in the expected repos."""

        command = re.sub(
            r"\s+",
            " ",
            f"""
repobee -p gitea repos setup --bu https://gitea.test.local/api/v1
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --template-org-name {giteamanager.TEMPLATE_ORG_NAME}
    --students {' '.join([t.members[0] for t in giteamanager.STUDENT_TEAMS])}
    --assignments task-1 task-2 task-3
    --tb
""",
        )

        run_in_docker_with_coverage(command, extra_args=extra_args)

        for team, template_name in itertools.product(
            giteamanager.STUDENT_TEAMS, template_helpers.TEMPLATE_REPO_NAMES
        ):
            repo_name = plug.generate_repo_name(team, template_name)
            sha = git.Repo(
                giteamanager.REPOSITORIES_ROOT
                / giteamanager.TARGET_ORG_NAME
                / (repo_name + ".git")
            ).head.commit.tree.hexsha
            assert template_helpers.TASK_CONTENTS_SHAS[template_name] == sha
