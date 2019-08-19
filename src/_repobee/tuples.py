"""Tuples module.

This module contains various namedtuple containers used throughout _repobee.
There are still a few namedtuples floating about in their own modules, but
the goal is to collect all container types in this module.

.. module:: tuples
    :synopsis: Module containing various namedtuple containers used throughout
        _repobee.

.. moduleauthor:: Simon Larsén
"""
from collections import namedtuple

Deprecation = namedtuple("Deprecation", ["replacement", "remove_by"])
