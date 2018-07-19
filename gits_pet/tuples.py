"""Tuples module.

This module contains various namedtuple containers used throughout gits_pet.
"""
from collections import namedtuple

Issue = namedtuple('Issue', ('title', 'body'))

Args = namedtuple(
    'Args',
    ('subparser', 'org_name', 'github_base_url', 'user', 'master_repo_urls',
     'master_repo_names', 'students', 'issue', 'title_regex'))
Args.__new__.__defaults__ = (None, ) * len(Args._fields)

Team = namedtuple('Team', ('name', 'members', 'id'))

RepoInfo = namedtuple(
    'RepoInfo', ('name', 'description', 'private', 'team_id'))
