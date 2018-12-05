"""Tuples module.

This module contains various namedtuple containers used throughout repomate.
There are still a few namedtuples floating about in their own modules, but
the goal is to collect all container types in this module.

.. module:: tuples
    :synopsis: Module containing various namedtuple containers used throughout repomate.

.. moduleauthor:: Simon Larsén
"""
from collections import namedtuple


class Issue(
        namedtuple('Issue',
                   ('title', 'body', 'number', 'created_at', 'author'))):
    def __new__(cls, title, body, number=None, created_at=None, author=None):
        return super().__new__(cls, title, body, number, created_at, author)


Args = namedtuple(
    'Args',
    ('subparser', 'org_name', 'github_base_url', 'user', 'master_repo_urls',
     'master_repo_names', 'students', 'issue', 'title_regex', 'traceback',
     'state', 'show_body', 'author', 'num_reviews'))
Args.__new__.__defaults__ = (None, ) * len(Args._fields)

Team = namedtuple('Team', ('name', 'members', 'id'))


class Repo(
        namedtuple('Repo',
                   ('name', 'description', 'private', 'team_id', 'url'))):
    def __new__(cls, name, description, private, team_id=None, url=None):
        return super().__new__(cls, name, description, private, team_id, url)


Review = namedtuple('Review', ['repo', 'done'])
