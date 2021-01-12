import random
import re
import shlex

import git

import repobee_plug as plug
import repobee
from repobee_testhelpers._internal import templates as template_helpers
from repobee_testhelpers.funcs import hash_directory
from _repobee.ext import gitea
from _repobee.hash import salted_hash

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

    def test_double_blind_generates_anonymous_teams_and_repos(
        self, target_api, with_student_repos, tmp_path_factory
    ):
        # arrange
        random.seed(1)
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]
        double_blind_salt = "12345"
        num_reviews = 1

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
    --double-blind-salt {double_blind_salt}
    --num-reviews {num_reviews}
    --tb
""",
        )

        # act
        repobee.run(shlex.split(command), plugins=[gitea])

        # assert
        for student_team in giteamanager.STUDENT_TEAMS:
            review_team_name = salted_hash(
                plug.generate_review_team_name(student_team, assignment_name),
                salt=double_blind_salt,
                max_hash_size=20,
            )
            original_repo_name = plug.generate_repo_name(
                student_team, assignment_name
            )
            anonymous_repo_name = salted_hash(
                original_repo_name, salt=double_blind_salt, max_hash_size=20
            )

            review_team, *other_teams = list(
                target_api.get_teams([review_team_name])
            )
            anonymous_repo, *other_repos = list(
                target_api.get_team_repos(review_team)
            )
            original_repo = target_api.get_repo(
                original_repo_name, student_team.name
            )

            assert not other_teams
            assert not other_repos

            assert len(review_team.members) == num_reviews
            assert not any(
                map(review_team.members.__contains__, student_team.members)
            )
            assert anonymous_repo.name == anonymous_repo_name

            workdir = tmp_path_factory.mktemp("workdir")
            anon_repo = git.Repo.clone_from(
                target_api.insert_auth(anonymous_repo.url),
                to_path=workdir / "anonymous",
            )
            orig_repo = git.Repo.clone_from(
                target_api.insert_auth(original_repo.url),
                to_path=workdir / "original",
            )

            assert hash_directory(
                orig_repo.working_tree_dir
            ) == hash_directory(anon_repo.working_tree_dir)
