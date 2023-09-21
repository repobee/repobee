import random
import re
import shlex

import git
import pytest

import repobee_plug as plug
import repobee
from repobee_testhelpers._internal import templates as template_helpers
from repobee_testhelpers.funcs import hash_directory
from _repobee.ext import gitea
from _repobee.hash import keyed_hash

import giteamanager


class TestAssign:
    def test_assignees_are_not_assigned(self, target_api, with_student_repos):
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
        double_blind_key = "12345"
        num_reviews = 1

        # act
        assign_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # assert
        for student_team in giteamanager.STUDENT_TEAMS:
            review_team_name = keyed_hash(
                student_team.name, key=double_blind_key, max_hash_size=20
            )
            original_repo_name = plug.generate_repo_name(
                student_team, assignment_name
            )
            anonymous_repo_name = keyed_hash(
                original_repo_name, key=double_blind_key, max_hash_size=20
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


class TestEnd:
    def test_end_double_blind_reviews_removes_review_teams(
        self, target_api, with_student_repos
    ):
        # arrange
        random.seed(1)
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]
        double_blind_key = "12345"
        num_reviews = 1
        assign_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # act
        end_reviews_with_key(assignment_name, double_blind_key)

        # assert
        review_team_names = [
            keyed_hash(
                student_team.name, key=double_blind_key, max_hash_size=20
            )
            for student_team in giteamanager.STUDENT_TEAMS
        ]
        fetched_review_teams = list(
            target_api.get_teams(team_names=review_team_names)
        )
        assert not fetched_review_teams

    def test_end_double_blind_reviews_removes_anonymous_repos(
        self, target_api, with_student_repos
    ):
        """Test that the anonymous repo copies are removed, but not the
        original repos.
        """
        # arrange
        random.seed(1)
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]
        double_blind_key = "12345"
        num_reviews = 1
        assign_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # act
        end_reviews_with_key(assignment_name, double_blind_key)

        # assert
        assert_iterations = 0
        for student_team in giteamanager.STUDENT_TEAMS:
            repo_name = plug.generate_repo_name(student_team, assignment_name)
            anonymous_repo_name = keyed_hash(
                repo_name, key=double_blind_key, max_hash_size=20
            )

            with pytest.raises(plug.NotFoundError):
                target_api.get_repo(anonymous_repo_name, student_team.name)

            assert target_api.get_repo(repo_name, student_team.name)

            assert_iterations += 1

        assert assert_iterations > 0

    def test_end_double_blind_reviews_does_not_remove_non_anonymous_repos(
        self, target_api, with_student_repos
    ):
        """Test that adding repos that are not the anonymous repo copies to the
        anonymous review teams does NOT cause them to be deleted. That would be
        badness.
        """
        # arrange
        random.seed(1)
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]
        double_blind_key = "12345"
        num_reviews = 1
        assign_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # add an original repo to one of the review teams
        orig_team_name = giteamanager.STUDENT_TEAMS[0].name
        orig_repo_name = plug.generate_repo_name(
            orig_team_name, assignment_name
        )
        orig_repo = target_api.get_repo(orig_repo_name, orig_team_name)
        review_team_name = keyed_hash(
            orig_team_name, key=double_blind_key, max_hash_size=20
        )
        review_team = next(target_api.get_teams([review_team_name]))
        target_api.assign_repo(
            review_team, orig_repo, plug.TeamPermission.PULL
        )

        # act
        end_reviews_with_key(assignment_name, double_blind_key)

        # assert
        assert target_api.get_repo(orig_repo_name, orig_team_name) == orig_repo


class TestCheck:
    def test_check_double_blind_review_contains_original_repo_names(
        self, target_api, with_student_repos, capsys
    ):
        """Weak test for checking double-blind review: just verify that the
        original repo names are contained in the output.
        """
        # arrange
        random.seed(1)
        assignment_name = template_helpers.TEMPLATE_REPO_NAMES[0]
        double_blind_key = "12345"
        num_reviews = 1
        assign_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # act
        check_reviews_with_key(assignment_name, num_reviews, double_blind_key)

        # assert
        expected_repo_names = plug.generate_repo_names(
            giteamanager.STUDENT_TEAMS, [assignment_name]
        )
        sout = capsys.readouterr().out
        for assert_iters, expected_repo_name in enumerate(expected_repo_names):
            assert expected_repo_name in sout

        assert assert_iters > 0


def check_reviews_with_key(
    assignment_name: str, num_reviews, key: str
) -> None:
    command = re.sub(
        r"\s+",
        " ",
        f"""
reviews check --bu {giteamanager.API_URL}
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --students {' '.join(map(str, giteamanager.STUDENT_TEAMS))}
    --assignments {assignment_name}
    --double-blind-key {key}
    --num-reviews {num_reviews}
    --title-regex Review
    --tb
""",
    )
    repobee.run(shlex.split(command), plugins=[gitea])


def end_reviews_with_key(assignment_name: str, key: str) -> None:
    command = re.sub(
        r"\s+",
        " ",
        f"""
reviews end --bu {giteamanager.API_URL}
    --token {giteamanager.TEACHER_TOKEN}
    --user {giteamanager.TEACHER_USER}
    --org-name {giteamanager.TARGET_ORG_NAME}
    --students {' '.join(map(str, giteamanager.STUDENT_TEAMS))}
    --assignments {assignment_name}
    --double-blind-key {key}
    --tb
        """,
    )
    repobee.run(shlex.split(command), plugins=[gitea])


def assign_reviews_with_key(
    assignment_name: str, num_reviews: int, key: str
) -> None:
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
    --double-blind-key {key}
    --num-reviews {num_reviews}
    --tb
""",
    )
    repobee.run(shlex.split(command), plugins=[gitea])
