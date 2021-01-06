import shlex
import re
import itertools

import git

import repobee

import repobee_plug as plug

from repobee_testhelpers._internal import templates as template_helpers

import giteamanager

from _repobee.ext import gitea


class TestSetup:
    def test_setup_once(self):
        """Test that running setup once results in the expected repos."""

        command = re.sub(
            r"\s+",
            " ",
            f"""
repos setup --bu https://localhost:3000/api/v1
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --template-org-name {giteamanager.TEMPLATE_ORG_NAME}
    --students {' '.join([t.members[0] for t in giteamanager.STUDENT_TEAMS])}
    --assignments {' '.join(template_helpers.TEMPLATE_REPO_NAMES)}
    --tb
""",
        )

        repobee.run(shlex.split(command), plugins=[gitea])

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
