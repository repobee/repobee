"""Specification for RepoBee's core CLI categories and actions."""
import enum
import itertools

from typing import Iterator

from repobee_plug.cli.categorization import Category, Action
from repobee_plug._immutable import ImmutableMixin


class _CoreCommand(ImmutableMixin):
    """The core CLI specification for RepoBee. Specifies the categories and
    their actions.
    """

    def iter_actions(self) -> Iterator[Action]:
        """Iterate over all command actions."""
        return iter(self)

    def __call__(self, key):
        category_map = {c.name: c for c in self._categories}
        if key not in category_map:
            raise ValueError(f"No such category: '{key}'")
        return category_map[key]

    def __iter__(self) -> Iterator[Action]:
        return itertools.chain.from_iterable(map(iter, self._categories))

    def __len__(self):
        return sum(map(len, self._categories))

    @property
    def _categories(self):
        return [
            attr
            for attr in self.__class__.__dict__.values()
            if isinstance(attr, Category)
        ]

    class _Repos(Category):
        setup: Action
        update: Action
        clone: Action
        migrate: Action

    class _Issues(Category):
        open: Action
        close: Action
        list: Action

    class _Config(Category):
        show: Action
        verify: Action

    class _Reviews(Category):
        assign: Action
        check: Action
        end: Action

    class _Teams(Category):
        create: Action

    repos = _Repos()
    issues = _Issues()
    config = _Config()
    reviews = _Reviews()
    teams = _Teams()


class BaseParser(enum.Enum):
    """Enumeration of base parsers that an extension command can request to
    have added to it.

    Attributes:
        BASE: Represents the base parser, which includes the ``--user``,
            ``--org-name``, ``--base-url`` and ``--token`` arguments.
        STUDENTS: Represents the students parser, which includes the
            ``--students`` and `--students-file`` arguments.
        ASSIGNMENTS: Represents the assignments parser, which includes the
            ``--assignments`` argument.
        REPO_DISCOVERY: Represents the repo discovery parser, which adds
            both the ``--assignments`` and the ``--discover-repos``
            arguments.
        TEMPLATE_ORG: Represents the master organization parser, which includes
            the ``--master-org`` argument.
    """

    BASE = "base"
    STUDENTS = "students"
    ASSIGNMENTS = "assignments"
    REPO_DISCOVERY = "repo-discovery"
    TEMPLATE_ORG = "template-org"
