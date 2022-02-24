"""Plugin that squashes template repos before they are pushed to students.

.. warning::

    Using this plugin makes it impossible to push updates to student repos
    using the ``repos update`` command. The fallback issue will always be
    opened, regardless of if the student has pushed anything or not.
"""
import datetime
import hashlib
import shlex
import subprocess

import repobee_plug as plug

import _repobee.git


class Squash(plug.Plugin, plug.cli.CommandExtension):
    __settings__ = plug.cli.command_extension_settings(
        actions=[plug.cli.CoreCommand.repos.setup]
    )

    squash_message = plug.cli.option(
        "--squash-message",
        help="commit message to use for the squash commit",
        converter=str,
        default="Initial commit",
        configurable=True,
    )

    def pre_setup(
        self, repo: plug.TemplateRepo, api: plug.PlatformAPI
    ) -> None:
        initial_branch = _repobee.git.active_branch(repo.path)
        tmp_branch = hashlib.sha256(
            str(datetime.datetime.now()).replace(" ", "_").encode("utf8")
        ).hexdigest()

        def _git(command: str) -> None:
            subprocess.run(
                ["git"] + shlex.split(command), cwd=repo.path, check=True
            )

        _git(f"symbolic-ref HEAD refs/heads/{tmp_branch}")
        _git("add .")
        _git(f"commit -m '{self.squash_message}'")
        _git(f"branch -D {initial_branch}")
        _git(f"branch -m '{initial_branch}'")
