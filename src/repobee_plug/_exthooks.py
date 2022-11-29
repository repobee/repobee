"""Hookspecs for repobee extension hooks.

Extension hooks add something to the functionality of repobee, but are not
necessary for its operation. Currently, all extension hooks are related to
cloning repos.

.. module:: exthooks
    :synopsis: Hookspecs for repobee extension hooks.
"""

import argparse
import configparser
from typing import Optional

from repobee_plug.cli.args import ConfigurableArguments
from repobee_plug.platform import PlatformAPI
from repobee_plug.hook import hookspec, Result
from repobee_plug.deprecation import deprecate
from repobee_plug.config import Config

from repobee_plug.localreps import StudentRepo, TemplateRepo


#########################
# Hooks for repos clone #
#########################


@hookspec
def post_clone(repo: StudentRepo, api: PlatformAPI) -> Optional[Result]:
    """Operate on a student repository after it has been cloned.

    Args:
        repo: A local representation of a student repo. The ``path``
            attribute is always set to a valid directory containing the
            repo.
        api: An instance of the platform API.
    Returns:
        Optionally returns a Result for reporting the outcome of the hook.
        May also return None, in which case no reporting will be performed
        for the hook.
    """


@deprecate(remove_by_version="3.0.0", replacement="handle_parsed_args")
@hookspec
def clone_parser_hook(clone_parser: argparse.ArgumentParser) -> None:
    """Do something with the clone repos subparser before it is used used to
    parse CLI options. The typical task is to add options to it.

    .. danger::

        This hook no longer has any effect, it is only kept for testing
        purposes.

    Args:
        clone_parser: The ``clone`` subparser.
    """


#########################
# Hooks for repos setup #
#########################


@hookspec
def pre_setup(repo: TemplateRepo, api: PlatformAPI) -> Optional[Result]:
    """Operate on a template repository before it is distributed to
    students.

    .. note::

        Changes to the template repo can be persisted by comitting them, making
        on-the-fly preprocessing possible. An example of this would be squashing
        the commits of the template repo before pushing it to students. Note
        that making any commit makes it impossible to later update student
        repos with the ``repos update`` command, as on-the-fly commits are
        unique by timestamp.

    Args:
        repo: Representation of a local template repo.
        api: An instance of the platform API.
    Returns:
        Optionally returns a Result for reporting the outcome of the hook.
        May also return None, in which case no reporting will be performed
        for the hook.
    """


@hookspec
def post_setup(
    repo: StudentRepo, api: PlatformAPI, newly_created: bool
) -> Optional[Result]:
    """Operate on a student repo after the setup command has executed.

    Args:
        repo: A student repository.
        api: An instance of the platform API.
        newly_created: False if the student repo already existed.
    Returns:
        Optionally returns a Result for reporting the outcome of the hook.
        May also return None, in which case no reporting will be performed
        for the hook.
    """


############################
# Hooks for config/parsing #
############################


@hookspec
def get_configurable_args() -> ConfigurableArguments:  # type: ignore
    """Get the configurable arguments for a plugin.

    .. danger::

        This is not a public hook, don't implement this manually!

    Returns:
        The configurable arguments of a plugin.
    """


@deprecate(remove_by_version="3.8.0", replacement="handle_config")
@hookspec
def config_hook(config_parser: configparser.ConfigParser) -> None:
    """Hook into the config file parsing.

    .. deprecated:: 3.6.0

        Use :py:func:`handle_config` instead.

    Args:
        config_parser: The config parser after config has been read.
    """


@hookspec
def handle_config(config: Config) -> None:
    """Handle the config.

    This hook is allowed both to read the config, and to modify it before it's
    passed to the core RepoBee application.

    .. warning::

        The :py:class:`Config` class is currently not stable and its behavior
        may change.

    Args:
        config: RepoBee's config.
    """


@hookspec
def handle_parsed_args(args: argparse.Namespace) -> None:
    """Handle the parsed args from the parser, before any processing is
    applied.

    Args:
        args: The full namespace returned by
            :py:func:`argparse.ArgumentParser.parse_args`
    """


@hookspec
def handle_processed_args(args: argparse.Namespace) -> None:
    """Handle the parsed command line arguments after RepoBee has applied
    processing.

    Args:
        args: A processed version of the parsed CLI arguments.
    """
