"""Tuples module.

This module contains various namedtuple containers used throughout gits_pet.
"""
from collections import namedtuple

Issue = namedtuple('Issue', ('title', 'body'))

Args = namedtuple(
    'Args',
    ('subparser', 'org_name', 'github_base_url', 'user', 'master_repo_urls',
     'master_repo_names', 'students', 'issue', 'title_regex'))
