"""This is a test plugin for the setup_task hook. It serves no real purpose.

.. module:: preflight
    :synopsis: Test plugin for the setup_task hook.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import repobee_plug as plug


def act(path: pathlib.Path, api: plug.API):
    return plug.Result(
        name="preflight",
        msg="Successful preflight on {}".format(path),
        status=plug.Status.SUCCESS,
    )


@plug.repobee_hook
def setup_task() -> plug.Task:
    return plug.Task(act=act)
