"""Tuples module.

This module contains various namedtuple containers used throughout gits_pet.
"""
from collections import namedtuple

Issue = namedtuple('Issue', ('title', 'body'))
