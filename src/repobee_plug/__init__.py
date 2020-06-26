import pluggy

from repobee_plug.__version import __version__  # noqa: F401

# Plugin stuff
from repobee_plug._pluginmeta import Plugin
from repobee_plug._containers import hookimpl as repobee_hook

# Containers
from repobee_plug._containers import Review
from repobee_plug._containers import Result
from repobee_plug._containers import Status
from repobee_plug._containers import ExtensionParser
from repobee_plug._containers import ExtensionCommand
from repobee_plug._containers import ReviewAllocation
from repobee_plug._containers import BaseParser
from repobee_plug._containers import Deprecation
from repobee_plug._containers import HookResult
from repobee_plug._tasks import Task

# Hook functions
from repobee_plug._corehooks import PeerReviewHook as _peer_hook
from repobee_plug._corehooks import APIHook as _api_hook
from repobee_plug._exthooks import CloneHook as _clone_hook
from repobee_plug._exthooks import TaskHooks as _task_hooks
from repobee_plug._exthooks import ExtensionCommandHook as _ext_command_hook

# Helpers
from repobee_plug._deprecation import deprecate, deprecated_hooks
from repobee_plug._serialize import (
    json_to_result_mapping,
    result_mapping_to_json,
)
from repobee_plug._name import (
    generate_repo_name,
    generate_repo_names,
    generate_review_team_name,
)

# API wrappers
from repobee_plug._apimeta import (
    Team,
    TeamPermission,
    Issue,
    IssueState,
    Repo,
    API,
    APISpec,
)

# Exceptions
from repobee_plug._exceptions import (
    ExtensionCommandError,
    HookNameError,
    PlugError,
)

manager = pluggy.PluginManager(__package__)
manager.add_hookspecs(_clone_hook)
manager.add_hookspecs(_peer_hook)
manager.add_hookspecs(_api_hook)
manager.add_hookspecs(_ext_command_hook)
manager.add_hookspecs(_task_hooks)

__all__ = [
    # Plugin stuff
    "Plugin",
    "repobee_hook",
    "manager",
    # Containers
    "Result",
    "HookResult",
    "Status",
    "ExtensionParser",
    "ExtensionCommand",
    "ReviewAllocation",
    "Review",
    "Task",
    "Deprecation",
    # API wrappers
    "Team",
    "TeamPermission",
    "Issue",
    "Repo",
    "Issue",
    "IssueState",
    "API",
    "APISpec",
    # Exceptions
    "ExtensionCommandError",
    "HookNameError",
    "PlugError",
    # Helpers
    "json_to_result_mapping",
    "result_mapping_to_json",
    "BaseParser",
    "generate_repo_name",
    "generate_repo_names",
    "generate_review_team_name",
    "deprecate",
    "deprecated_hooks",
]
