"""This is a test plugin for the setup_task hook. It serves no real purpose.

.. module:: javac
    :synopsis: Plugin that tries to compile all .java files in a repo.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import repobee_plug as plug


def callback(path: pathlib.Path, api: plug.API):
    return plug.HookResult(
        hook="preflight",
        msg="Successful preflight on {}".format(path),
        status=plug.Status.SUCCESS,
    )


@plug.repobee_hook
def setup_task() -> plug.Task:
    return plug.Task(callback=callback)
