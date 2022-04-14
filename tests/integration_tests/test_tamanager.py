"""Integration tests for the tamanager plugin."""
from typing import List

from repobee_testhelpers import funcs
from repobee_testhelpers import const
from repobee_testhelpers import localapi

from _repobee.ext import tamanager


def test_post_setup_adds_student_repos_to_teacher_team(platform_url):
    """The post_setup hook should add freshly created student repos to the
    teachers team.
    """
    funcs.run_repobee(
        f"repos setup -a {const.TEMPLATE_REPOS_ARG} "
        f"--base-url {platform_url}",
        plugins=[tamanager],
    )

    teachers_team = get_teachers_team(platform_url)
    num_expected_repos = len(const.STUDENT_TEAMS) * len(
        const.TEMPLATE_REPO_NAMES
    )
    assert len(teachers_team.repos) == num_expected_repos
    expected_repo_names = [r.name for r in funcs.get_repos(platform_url)]
    actual_repo_names = [r.name for r in teachers_team.repos]
    assert sorted(expected_repo_names) == sorted(actual_repo_names)


def test_add_teachers_command_happy_path(platform_url):
    """The add-teachers command should add all existing repos to the teachers
    team, as well as the specified teachers.
    """
    # arrange
    teachers = ["gork", "mork", "slanesh"]
    setup_student_repos_and_user_accounts(teachers, platform_url)

    # act
    funcs.run_repobee(
        f"teams add-teachers --teachers {' '.join(teachers)} "
        f"--base-url {platform_url}",
        plugins=[tamanager],
    )

    # assert
    teachers_team = get_teachers_team(platform_url)
    num_expected_repos = len(const.STUDENT_TEAMS) * len(
        const.TEMPLATE_REPO_NAMES
    )
    assert len(teachers_team.repos) == num_expected_repos
    expected_repo_names = [r.name for r in funcs.get_repos(platform_url)]
    actual_repo_names = [r.name for r in teachers_team.repos]
    assert sorted(expected_repo_names) == sorted(actual_repo_names)
    assert sorted([m.username for m in teachers_team.members]) == sorted(
        teachers
    )


def test_add_teachers_twice(platform_url):
    """The effect of running add-teachers once or twice should be identical."""
    # arrange
    teachers = ["gork", "mork", "slanesh"]
    setup_student_repos_and_user_accounts(teachers, platform_url)

    # act
    for _ in range(2):
        funcs.run_repobee(
            f"teams add-teachers --teachers {' '.join(teachers)} "
            f"--base-url {platform_url}",
            plugins=[tamanager],
        )

    # assert
    teachers_team = get_teachers_team(platform_url)
    num_expected_repos = len(const.STUDENT_TEAMS) * len(
        const.TEMPLATE_REPO_NAMES
    )
    assert len(teachers_team.repos) == num_expected_repos
    expected_repo_names = [r.name for r in funcs.get_repos(platform_url)]
    actual_repo_names = [r.name for r in teachers_team.repos]
    assert sorted(expected_repo_names) == sorted(actual_repo_names)
    assert sorted([m.username for m in teachers_team.members]) == sorted(
        teachers
    )


def setup_student_repos_and_user_accounts(
    usernames: List[str], platform_url: str
):
    funcs.run_repobee(
        f"repos setup -a {const.TEMPLATE_REPOS_ARG} "
        f"--base-url {platform_url}",
    )
    api = funcs.get_api(platform_url)
    api._add_users(usernames)


def get_teachers_team(platform_url: str) -> localapi.Team:
    """Helpe function to fetch the teachers team."""
    return next(
        filter(
            lambda team: team.name == tamanager.TEACHERS_TEAM_NAME,
            funcs.get_teams(platform_url),
        )
    )
