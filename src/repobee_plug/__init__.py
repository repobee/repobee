import pluggy  # type: ignore

from repobee_plug.__version import __version__  # noqa: F401

# Plugin stuff
from repobee_plug._pluginmeta import Plugin
from repobee_plug.hook import hookimpl as repobee_hook
from repobee_plug import cli
from repobee_plug.cli.io import echo
from repobee_plug.cli import BaseParser
from repobee_plug import log
from repobee_plug.cli.args import ConfigurableArguments

# Hook stuff
from repobee_plug.hook import Status, Result

# Review stuff
from repobee_plug.reviews import Review, ReviewAllocation

# Hook functions
from repobee_plug._corehooks import PeerReviewHook as _peer_hook
from repobee_plug._corehooks import APIHook as _api_hook
from repobee_plug._exthooks import CloneHook as _clone_hook
from repobee_plug._exthooks import SetupHook as _setup_hook
from repobee_plug._exthooks import ConfigHook as _config_hook

# Helpers
from repobee_plug.deprecation import deprecate, deprecated_hooks, Deprecation
from repobee_plug._serialize import (
    json_to_result_mapping,
    result_mapping_to_json,
)
from repobee_plug.name import (
    generate_repo_name,
    generate_repo_names,
    generate_review_team_name,
)
from repobee_plug import fileutils

# API wrappers
from repobee_plug.platform import (
    Team,
    TeamPermission,
    Issue,
    IssueState,
    Repo,
    PlatformAPI,
    _APISpec,
)

# Exceptions
from repobee_plug.exceptions import (
    HookNameError,
    PlugError,
    PlatformError,
    NotFoundError,
    ServiceNotFoundError,
    BadCredentials,
    UnexpectedException,
    InvalidURL,
)

# Local representations
from repobee_plug.localreps import StudentTeam, StudentRepo, TemplateRepo

manager = pluggy.PluginManager(__package__)
manager.add_hookspecs(_clone_hook)
manager.add_hookspecs(_setup_hook)
manager.add_hookspecs(_peer_hook)
manager.add_hookspecs(_api_hook)
manager.add_hookspecs(_config_hook)

__all__ = [
    # Plugin stuff
    "Plugin",
    "repobee_hook",
    "manager",
    "echo",
    # Containers
    "Result",
    "Status",
    "ReviewAllocation",
    "Review",
    "Deprecation",
    "ConfigurableArguments",
    # Local representations
    "StudentTeam",
    "StudentRepo",
    "TemplateRepo",
    # API wrappers
    "Team",
    "TeamPermission",
    "Issue",
    "Repo",
    "Issue",
    "IssueState",
    "PlatformAPI",
    "_APISpec",
    # Exceptions
    "HookNameError",
    "PlugError",
    "PlatformError",
    "NotFoundError",
    "ServiceNotFoundError",
    "BadCredentials",
    "UnexpectedException",
    "InvalidURL",
    # Helpers
    "json_to_result_mapping",
    "result_mapping_to_json",
    "BaseParser",
    "generate_repo_name",
    "generate_repo_names",
    "generate_review_team_name",
    "deprecate",
    "deprecated_hooks",
    # Modules/Packages
    "cli",
    "fileutils",
    "log",
]
