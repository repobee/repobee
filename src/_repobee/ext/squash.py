"""Plugin that squashes template repos before they are pushed to students.
"""
import datetime
import hashlib
import shlex

import repobee_plug as plug
import subprocess

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

    def preprocess_template(
        self, repo: plug.TemplateRepo, api: plug.PlatformAPI
    ) -> None:
        assert repo.path

        initial_branch = _repobee.git.active_branch(repo.path)
        tmp_branch = hashlib.sha1(
            str(datetime.datetime.now()).replace(" ", "_").encode("utf8")
        ).hexdigest()

        subprocess.run(
            f"git symbolic-ref HEAD refs/heads/{tmp_branch}".split(),
            cwd=repo.path,
        )
        subprocess.run("git add .".split(), cwd=repo.path)
        subprocess.run(
            shlex.split(f"git commit -m '{self.squash_message}'"),
            cwd=repo.path,
        )
        subprocess.run(
            shlex.split(f"git branch -D {initial_branch}"), cwd=repo.path
        )
        subprocess.run(
            shlex.split(f"git branch -m '{initial_branch}'"), cwd=repo.path
        )
