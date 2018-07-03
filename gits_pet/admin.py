"""Functions for administrating repos.

This module contains functions for administrating repositories, such as
creating student repos from some master repo template. Currently, the
philosophy is that each student has an associated team with the same
name as the student's username. The team is then granted access to repos.

Each public function in this module is to be treated as a self-contained
program.
"""

import shutil
import os
from typing import Iterable, List
import daiquiri
from gits_pet import git
from gits_pet import util
from gits_pet.github_api import GitHubAPI, RepoInfo
from gits_pet.api_wrapper import Team
from gits_pet.git import Push

LOGGER = daiquiri.getLogger(__file__)


def create_multiple_student_repos(master_repo_urls: Iterable[str], user: str,
                                  students: Iterable[str], org_name: str,
                                  github_api_base_url: str):
    """Create one student repo for each of the master repos in master_repo_urls.

    Args:
        master_repo_url: Url to a template repository for the student repos.
        user: Username of the administrator that is creating the repos.
        students: An iterable of student GitHub usernames.
        org_name: Name of an organization.
        github_api_base_url: The base url to a GitHub api.
    """
    util.validate_types(
        user=(user, str),
        org_name=(org_name, str),
        github_api_base_url=(github_api_base_url, str))
    util.validate_non_empty(
        master_repo_urls=master_repo_urls,
        user=user,
        students=students,
        org_name=org_name,
        github_api_base_url=github_api_base_url)

    urls = list(master_repo_urls)  # safe copy

    if len(set(urls)) != len(urls):
        raise ValueError("master_repo_urls contains duplicates")

    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)

    for url in urls:
        git.clone(url)

    # (team_name, member list) mappings, each student gets its own team
    member_lists = {student: [student] for student in students}
    teams = api.ensure_teams_and_members(member_lists)

    repo_infos = _create_repo_infos(urls, teams)

    LOGGER.info("creating student repos ...")
    repo_urls = api.create_repos(repo_infos)

    push_tuples = _create_push_tuples(urls, repo_urls)

    LOGGER.info("pushing files to student repos ...")
    git.push_many(push_tuples, user=user)

    _remove_local_repos(urls)


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
            name=generate_repo_name(team.name, repo_base_name),
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


def update_student_repos(master_repo_urls: Iterable[str], user: str,
                         students: Iterable[str], org_name: str,
                         github_api_base_url: str) -> None:
    """Attempt to update all student repos related to one of the master repos.
    
    Args:
        master_repo_urls: URLs to template repositories for the student repos.
        user: Username of the administrator that is creating the repos.
        students: Student GitHub usernames.
        org_name: Name of the organization.
        github_api_base_url: The base url to a GitHub api.
    """
    util.validate_types(
        user=(user, str),
        org_name=(org_name, str),
        github_api_base_url=(github_api_base_url, str))
    util.validate_non_empty(
        master_repo_urls=master_repo_urls,
        user=user,
        students=students,
        org_name=org_name,
        github_api_base_url=github_api_base_url)
    urls = list(master_repo_urls)  # safe copy

    if len(set(urls)) != len(urls):
        raise ValueError("master_repo_urls contains duplicates")

    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)

    urls = list(master_repo_urls)
    master_repo_names = [_repo_name(url) for url in urls]
    student_repo_names = [
        generate_repo_name(student, master_repo_name) for student in students
        for master_repo_name in master_repo_names
    ]

    repo_urls = api.get_repo_urls(student_repo_names)

    LOGGER.info("cloning into master repos ...")
    for url in urls:
        git.clone(url)

    push_tuples = _create_push_tuples(urls, repo_urls)

    LOGGER.info("pushing files to student repos ...")
    git.push_many(push_tuples, user=user)

    _remove_local_repos(urls)
    LOGGER.info("done!")


def open_issue(master_repo_names: Iterable[str], students: Iterable[str],
               issue_path: str, user: str, org_name: str,
               github_api_base_url: str) -> None:
    """Open an issue in student repos.

    Args:
        master_repo_names: Names of master repositories.
        students: Student GitHub usernames.
        issue_path: Filepath to a markdown file. The first line is assumed to
        be the title.
        user: Username of the administrator that is creating the repos.
        org_name: Name of the organization.
        github_api_base_url: The base url to a GitHub api.
    """
    util.validate_types(
        user=(user, str),
        org_name=(org_name, str),
        github_api_base_url=(github_api_base_url, str))
    util.validate_non_empty(
        master_repo_names=master_repo_names,
        user=user,
        students=students,
        org_name=org_name,
        github_api_base_url=github_api_base_url)
    if not os.path.isfile(issue_path):
        raise ValueError("issue_path: '{}' is not a file".format(issue_path))

    with open(issue_path, 'r') as f:
        title = f.readline().strip()
        body = f.read()

    repo_names = [
        generate_repo_name(student, master) for master in master_repo_names
        for student in students
    ]

    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)

    api.open_issue(title, body, repo_names)


def close_issue(title_regex: str, master_repo_names: Iterable[str],
                students: Iterable[str], user: str, org_name: str,
                github_api_base_url: str) -> None:
    """Close issues whose titles match the title_regex in student repos.

    Args:
        title_regex: A regex to match against issue titles.
        master_repo_names: Names of master repositories.
        students: Student GitHub usernames.
        user: Username of the administrator that is creating the repos.
        org_name: Name of the organization.
        github_api_base_url: The base url to a GitHub api.
    """
    util.validate_types(
        user=(user, str),
        org_name=(org_name, str),
        github_api_base_url=(github_api_base_url, str))
    util.validate_non_empty(
        master_repo_names=master_repo_names,
        user=user,
        students=students,
        org_name=org_name,
        github_api_base_url=github_api_base_url)

    repo_names = [
        generate_repo_name(student, master) for master in master_repo_names
        for student in students
    ]

    api = GitHubAPI(github_api_base_url, git.OAUTH_TOKEN, org_name)

    api.close_issue(title_regex, repo_names)


def generate_repo_name(team_name: str, master_repo_name: str) -> str:
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


def _create_repo_infos(urls: Iterable[str],
                       teams: Iterable[Team]) -> List[RepoInfo]:
    """Create RepoInfo namedtuples for all combinations of url and team.

    Args:
        urls: Master repo urls.
        teams: Team namedtuples.

    Returns:
        A list of RepoInfo namedtuples with all (url, team) combinations.
    """
    repo_infos = []
    for url in urls:
        repo_base_name = _repo_name(url)
        repo_infos += [
            RepoInfo(
                name=generate_repo_name(team.name, repo_base_name),
                description="{} created for {}".format(repo_base_name,
                                                       team.name),
                private=True,
                team_id=team.id) for team in teams
        ]
    return repo_infos


def _create_push_tuples(master_urls: Iterable[str],
                        repo_urls: Iterable[str]) -> List[Push]:
    """Create Push namedtuples for all repo urls in repo_urls that share
    repo base name with any of the urls in master_urls.

    Args:
        master_urls: Urls to master repos.
        repo_urls: Urls to student repos.

    Returns:
        A list of Push namedtuples for all student repo urls that relate to
        any of the master repo urls.
    """
    push_tuples = []
    for url in master_urls:
        repo_base_name = _repo_name(url)
        push_tuples += [
            git.Push(
                local_path=repo_base_name,
                remote_url=repo_url,
                branch='master') for repo_url in repo_urls
            if repo_url.endswith(repo_base_name)
        ]
    return push_tuples


def _remove_local_repos(urls: Iterable[str]) -> None:
    LOGGER.info("removing local repos ...")
    for url in urls:
        name = _repo_name(url)
        shutil.rmtree(name)
        LOGGER.info("removed {}".format(name))
