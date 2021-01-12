import re
import shlex

import repobee_plug as plug
import repobee
from repobee_testhelpers._internal import templates as template_helpers
from _repobee.ext import gitea

import giteamanager


class TestAssign:
    def test_asignees_are_not_assigned(self, target_api, with_student_repos):
        # arrange
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]

        command = re.sub(
            r"\s+",
            " ",
            f"""
reviews assign --bu {giteamanager.API_URL}
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --students {' '.join(map(str, giteamanager.STUDENT_TEAMS))}
    --assignments {assignment_name}
    --tb
""",
        )

        # act
        repobee.run(shlex.split(command), plugins=[gitea])

        # assert
        repos = [
            target_api.get_repo(
                plug.generate_repo_name(team, assignment_name), team.name
            )
            for team in giteamanager.STUDENT_TEAMS
        ]
        assert repos
        for repo in repos:
            issue = next(target_api.get_repo_issues(repo))
            assert not issue.implementation["assignees"]
