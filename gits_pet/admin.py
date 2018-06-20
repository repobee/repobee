"""Functions for administrating repos.

This module contains functions for administrating repositories, such as
creating student repos from some master repo template. Currently, the
philosophy is that each student has an associated team with the same
name as the student's username. The team is then granted access to repos.

Each public function in this module is to be treated as a self-contained
program.
"""

import shutil
from typing import Iterable
import daiquiri
from gits_pet import git
from gits_pet.github_api import (setup_api, ensure_teams_and_members,
                                 create_repos, RepoInfo)

LOGGER = daiquiri.getLogger(__file__)


def repo_name(team_name: str, master_repo_name: str) -> str:
    """Construct a repo name for a team.
    
    Args:
        team_name: Name of the associated team.
        master_repo_name: Name of the template repository.
    """
    return "{}-{}".format(team_name, master_repo_name)


def create_student_repos(master_repo_url: str,
                         user: str,
                         students: Iterable[str],
                         org_name: str,
                         github_api_base_url: str,
                         repo_base_name: str = None):
    """Create student repos from a master repo template.

    Args:
        master_repo_url: Url to a template repository for the student repos.
        user: Username of the administrator that is creating the repos.
        students: An iterable of student GitHub usernames.
        org_name: Name of an organization.
        github_api_base_url: The base url to a GitHub api.
        repo_base_name: The base name for all student repositories. If None,
        the base name of the master repo is used.
    """
    setup_api(github_api_base_url, git.OAUTH_TOKEN)

    master_repo_name = master_repo_url.split("/")[-1]
    if master_repo_name.endswith('.git'):
        master_repo_name = master_repo_name[:-4]

    LOGGER.info("cloning master repo {}...".format(master_repo_name))
    git.clone(master_repo_url)

    # (team_name, member list) mappings, each student gets its own team
    member_lists = {student: [student] for student in students}
    teams = ensure_teams_and_members(member_lists, org_name)

    if not repo_base_name:
        repo_base_name = master_repo_name

    repo_infos = [
        RepoInfo(
            name=repo_name(team.name, repo_base_name),
            description="{} created for {}".format(repo_base_name, team.name),
            private=True,
            team_id=team.id) for team in teams
    ]
    LOGGER.info("creating repos with base name {}...".format(repo_base_name))
    repo_urls = create_repos(repo_infos, org_name)

    LOGGER.info("adding push remotes to master repo...")
    git.add_push_remotes(master_repo_name, user,
                         [('origin', url) for url in repo_urls])
    LOGGER.info("pushing files to student repos...")
    git.push(master_repo_name)

    LOGGER.info("removing master repo ...")
    shutil.rmtree(master_repo_name)
    LOGGER.info("done!")
