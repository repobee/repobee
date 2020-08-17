"""Categorization classes for CLI commands."""
import abc
from typing import Tuple, Set, List, Mapping, Optional, Iterable, Union

from repobee_plug._containers import ImmutableMixin


class Category(ImmutableMixin, abc.ABC):
    """Class describing a command category for RepoBee's CLI. The purpose of
    this class is to make it easy to programmatically access the different
    commands in RepoBee.

    A full command in RepoBee typically takes the following form:

    .. code-block:: bash

        $ repobee <category> <action> [options ...]

    For example, the command ``repobee issues list`` has category ``issues``
    and action ``list``. Actions are unique only within their category.
    """

    help: str = ""
    description: str = ""
    name: str
    actions: Tuple["Action"]
    action_names: Set[str]
    _action_table: Mapping[str, "Action"]

    def __init__(
        self,
        name: Optional[str] = None,
        action_names: Optional[Set[str]] = None,
        help: Optional[str] = None,
        description: Optional[str] = None,
    ):
        # determine the name of this category based on the runtime type of the
        # inheriting class
        name = name or self.__class__.__name__.lower().strip("_")
        # determine the action names based on type annotations in the
        # inheriting class
        action_names = (action_names or set()) | {
            name
            for name, tpe in self.__annotations__.items()
            if isinstance(tpe, type) and issubclass(tpe, Action)
        }

        object.__setattr__(self, "help", help or self.help)
        object.__setattr__(
            self, "description", description or self.description
        )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "action_names", set(action_names))
        # This is just to reserve the name 'actions'
        object.__setattr__(self, "actions", None)

        for key in self.__dict__.keys():
            if key in action_names:
                raise ValueError(f"Illegal action name: {key}")

        actions = []
        for action_name in action_names:
            action = Action(action_name.replace("_", "-"), self)
            object.__setattr__(self, action_name.replace("-", "_"), action)
            actions.append(action)

        object.__setattr__(self, "actions", tuple(actions))
        object.__setattr__(self, "_action_table", {a.name: a for a in actions})

    def get(self, key: str) -> Optional["Action"]:
        return self._action_table.get(key)

    def __getitem__(self, key: str) -> "Action":
        return self._action_table[key]

    def __iter__(self) -> Iterable["Action"]:
        return iter(self.actions)

    def __len__(self):
        return len(self.actions)

    def __repr__(self):
        return f"Category(name={self.name}, actions={self.action_names})"

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(repr(self))

    def __getattr__(self, key):
        """We implement getattr such that linters won't complain about
        dynamically added members.
        """
        return object.__getattribute__(self, key)


class Action(ImmutableMixin):
    """Class describing a RepoBee CLI action.

    Attributes:
        name: Name of this action.
        category: The category this action belongs to.
    """

    name: str
    category: Category

    def __init__(self, name: str, category: Category):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)

    def __repr__(self):
        return f"<Action(name={self.name},category={self.category})>"

    def __str__(self):
        return f"{self.category.name} {self.name}"

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.name == other.name
            and self.category == other.category
        )

    def __hash__(self):
        return hash(str(self))

    def as_name_dict(self) -> Mapping[str, str]:
        """This is a convenience method for testing that returns a dictionary
        on the following form:

        .. code-block:: python

            {"category": self.category.name "action": self.name}

        Returns:
            A dictionary with the name of this action and its category.
        """
        return {"category": self.category.name, "action": self.name}

    def as_name_tuple(self) -> Tuple[str, str]:
        """This is a convenience method for testing that returns a tuple
        on the following form:

        .. code-block:: python

            (self.category.name, self.name)

        Returns:
            A dictionary with the name of this action and its category.
        """
        return (self.category.name, self.name)

    def astuple(self) -> Tuple["Category", "Action"]:
        """Same as :py:meth:`Action.as_name_tuple`, but with the proper
        :py:class:`Category` and :py:class:`Action` objects instead of strings.

        Returns:
            A tuple with the category and action.
        """
        return (self.category, self)

    def asdict(self) -> Mapping[str, Union["Category", "Action"]]:
        """Same as :py:meth:`Action.as_name_dict`, but with the proper
        :py:class:`Category` and :py:class:`Action` objects instead of strings.

        Returns:
            A dictionary with the category and action.
        """
        return {"category": self.category, "action": self}


def category(
    name: str, action_names: List[str], help: str = "", description: str = ""
) -> "Category":
    """Create a category for CLI actions.

    Args:
        name: Name of the category.
        action_names: The actions of this category.
    Returns:
        A CLI category.
    """
    return Category(
        name=name,
        action_names=set(action_names),
        help=help,
        description=description,
    )
