from repobee_plug.__version import __version__  # noqa: F401

from repobee_plug import types

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

# Helpers
from repobee_plug.deprecation import deprecate, deprecated_hooks, Deprecation
from repobee_plug.serialize import (
    json_to_result_mapping,
    result_mapping_to_json,
)
from repobee_plug.name import (
    generate_repo_name,
    generate_repo_names,
    generate_review_team_name,
)
from repobee_plug import fileutils
from repobee_plug.config import Config

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
    InternetConnectionUnavailable,
)

# Local representations
from repobee_plug.localreps import (
    StudentTeam,
    StudentRepo,
    TemplateRepo,
    normalize_name,
)

# Hook functions
from repobee_plug.hookmanager import manager
import repobee_plug._corehooks
import repobee_plug._exthooks

manager.add_hookspecs(repobee_plug._corehooks)
manager.add_hookspecs(repobee_plug._exthooks)

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
    "InternetConnectionUnavailable",
    # Helpers
    "json_to_result_mapping",
    "result_mapping_to_json",
    "BaseParser",
    "generate_repo_name",
    "generate_repo_names",
    "generate_review_team_name",
    "deprecate",
    "deprecated_hooks",
    "Config",
    "normalize_name",
    # Modules/Packages
    "cli",
    "fileutils",
    "log",
    "types",
]
