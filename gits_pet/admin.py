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
from gits_pet.github_api import GitHubAPI, RepoInfo

LOGGER = daiquiri.getLogger(__file__)


def repo_name(team_name: str, master_repo_name: str) -> str:
    """Construct a repo name for a team.
    
    Args:
        team_name: Name of the associated team.
        master_repo_name: Name of the template repository.
    """
    return "{}-{}".format(team_name, master_repo_name)


def _repo_name(repo_url):
    """Extract the name of the repo from its url.

    Args:
        repo_url: A url to a repo.
    """
    repo_name = repo_url.split("/")[-1]
    if repo_name.endswith('.git'):
        return repo_name[:-4]
    return repo_name


def create_multiple_student_repos(master_repo_urls: Iterable[str], user: str,
                                  students: Iterable[str], org_name: str,
                                  github_api_base_url: str):
    """Create one student repo for each of the master repos in master_repo_urls."""
    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)
    urls = list(master_repo_urls)  # safe copy

    if len(set(urls)) != len(urls):
        raise ValueError("master_repo_urls contains duplicates")

    for url in urls:
        git.clone(url)


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
    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)

    master_repo_name = _repo_name(master_repo_url)

    LOGGER.info("cloning master repo {}...".format(master_repo_name))
    git.clone(master_repo_url)

    # (team_name, member list) mappings, each student gets its own team
    member_lists = {student: [student] for student in students}
    teams = api.ensure_teams_and_members(member_lists)

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
    repo_urls = api.create_repos(repo_infos)

    git.push_many(
        (git.Push(
            local_path=master_repo_name, remote_url=repo_url, branch='master')
         for repo_url in repo_urls),
        user=user)

    LOGGER.info("removing master repo ...")
    shutil.rmtree(master_repo_name)
    LOGGER.info("done!")
