"""Task data structure and related functionality.

.. module:: tasks
    :synopsis: Task data structure and related functionality.

.. moduleauthor:: Simon Larsén
"""
import collections

from pathlib import Path
from argparse import ArgumentParser, Namespace
from typing import Callable, Optional

from repobee_plug._containers import Result
from repobee_plug._apimeta import API


class Task(
    collections.namedtuple(
        "Task", ("act", "add_option", "handle_args", "persist_changes")
    )
):
    """A data structure for describing a task. Tasks are operations that
    plugins can define to run on for example cloned student repos (a clone
    task) or on master repos before setting up student repos (a setup task).
    Only the ``act`` attribute is required, all other attributes can be
    omitted.

    The callback methods should have the following headers.

    .. code-block:: python

        def act(
            path: pathlib.Path, api: repobee_plug.API
        ) -> Optional[containers.Result]:

        def add_option(parser: argparse.ArgumentParser) -> None:

        def handle_args(args: argparse.Namespace) -> None:

    .. note::

        The functions are called in the following order: ``add_option`` ->
        ``handle_args`` -> ``act``.

    .. important::

        The ``act`` callback should *never* change the Git repository it acts
        upon (e.g. running commands such as ``git add``, ``git checkout`` or
        ``git commit``). This can have adverse and unexpected effects on
        RepoBee's functionality. It is however absolutely fine to change the
        files in the Git working tree, as long as nothing is added or
        committed.

    Each callback is called at most once. They are not guaranteed to execute,
    because there may be an unexpected crash somewhere else, or the plugin may
    not come into scope (for example, a clone task plugin will not come into
    scope if ``repobee setup`` is run). The callbacks can do whatever is
    appropriate for the plugin, except for changing any Git repositories. For
    information on the types used in the callbacks, see the Python stdlib
    documentation for :py:mod:`argparse`.

    As an example, a simple clone task can be defined like so:

    .. code-block:: python

        import repobee_plug as plug

        def act(path, api):
            return plug.Result(
                name="example",
                msg="IT LIVES!",
                status=plug.Status.SUCCESS
            )

        @plug.repobee_hook
        def clone_task():
            return plug.Task(act=act)

    If your task plugin also needs to access the configuration file, then
    implement the separate ``config_hook`` hook. For more elaborate
    instructions on creating tasks, see the tutorial.
    """

    def __new__(
        cls,
        act: Callable[[Path, API], Result],
        add_option: Optional[Callable[[ArgumentParser], None]] = None,
        handle_args: Optional[Callable[[Namespace], None]] = None,
        persist_changes: bool = False,
    ):
        return super().__new__(
            cls, act, add_option, handle_args, persist_changes
        )

    # The init method is just added for documentation purposes
    def __init__(
        self,
        act: Callable[[Path, API], Result],
        add_option: Optional[Callable[[ArgumentParser], None]] = None,
        handle_args: Optional[Callable[[Namespace], None]] = None,
        persist_changes: bool = False,
    ):
        """
        Args:
            act: A required callback function that takes the path to a
                repository worktree and an API instance, and optionally returns
                a Result to report results.
            add_option: An optional callback function that adds options to the
                CLI parser.
            handle_args: An optional callback function that receives the parsed
                CLI args.
            persist_changes: If True, the task requires that changes to the
                repository that has been acted upon be persisted. This means
                different things in different contexts (e.g.  whether the task
                is executed in a clone context or in a setup context), and may
                not be supported for all contexts.
        """
        super().__init__()
