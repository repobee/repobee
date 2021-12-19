"""Utility functions for dealing with URLs.

.. module:: urlutil
    :synopsis: Utility functions for dealing with URLs.

.. moduleauthor:: Simon Larsén
"""


def extract_repo_name(repo_url: str) -> str:
    """Extract the name of the repo from its url.

    Args:
        repo_url: A url to a repo.
    """
    repo_name = repo_url.split("/")[-1]
    if repo_name.endswith(".git"):
        return repo_name[:-4]
    return repo_name
