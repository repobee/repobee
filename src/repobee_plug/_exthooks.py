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

from repobee_plug.platform import PlatformAPI
from repobee_plug._containers import hookspec
from repobee_plug._containers import Result, ConfigurableArguments
from repobee_plug._deprecation import deprecate

from repobee_plug.localreps import StudentRepo, TemplateRepo


class CloneHook:
    """Hook functions related to cloning repos."""

    @hookspec
    def post_clone(
        self, repo: StudentRepo, api: PlatformAPI
    ) -> Optional[Result]:
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
    def clone_parser_hook(self, clone_parser: argparse.ArgumentParser) -> None:
        """Do something with the clone repos subparser before it is used used to
        parse CLI options. The typical task is to add options to it.

        .. danger::

            This hook no longer has any effect, it is only kept for testing
            purposes.

        .. deprecated:: 0.12.0

            This hook is has been replaced by
            :py:meth:`CloneHook.handle_parsed_args` and
            :py:meth:`CloneHook.handle_processed_args`. Once all known,
            existing plugins have been migrated to the new hook, this hook will
            be removed.

        Args:
            clone_parser: The ``clone`` subparser.
        """

    @hookspec
    def handle_parsed_args(self, args: argparse.Namespace) -> None:
        """Handle the parsed args from the parser, before any processing is
        applied.

        Args:
            args: The full namespace returned by
                :py:func:`argparse.ArgumentParser.parse_args`
        """

    @hookspec
    def handle_processed_args(self, args: argparse.Namespace) -> None:
        """Handle the parsed command line arguments after RepoBee has applied
        processing.

        Args:
            args: A processed version of the parsed CLI arguments.
        """

    @hookspec
    def config_hook(self, config_parser: configparser.ConfigParser) -> None:
        """Hook into the config file parsing.

        Args:
            config: the config parser after config has been read.
        """


class SetupHook:
    """Hook functions related to setting up repos."""

    @hookspec
    def pre_setup(
        self, repo: TemplateRepo, api: PlatformAPI
    ) -> Optional[Result]:
        """Operate on a template repository before it is distributed to
        students.

        .. note::

            Structural changes to the master repo are not currently supported.
            Changes to the repository during the callback will not be reflected
            in the generated repositories. Support for preprocessing is not
            planned as it is technically difficult to implement.

        Args:
            repo: Representation of a local template repo.
            api: An instance of the platform API.
        Returns:
            Optionally returns a Result for reporting the outcome of the hook.
            May also return None, in which case no reporting will be performed
            for the hook.
        """


class ConfigHook:
    """Hook functions related to configuration."""

    @hookspec
    def get_configurable_args(self) -> ConfigurableArguments:
        """Get the configurable arguments for a plugin.

        .. danger::

            This is not a public hook, don't implement this manually!

        Returns:
            The configurable arguments of a plugin.
        """
