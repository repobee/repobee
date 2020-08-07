"""This is a test plugin for the clone_task hook. It serves no real purpose.

.. module:: postflight
    :synopsis: Test plugin for the clone_task hook.

.. moduleauthor:: Simon Larsén
"""

import pathlib
import repobee_plug as plug


@plug.repobee_hook
def post_clone(path: pathlib.Path, api: plug.PlatformAPI):
    return plug.Result(
        name="postflight",
        msg="Successful postflight on {}".format(path),
        status=plug.Status.SUCCESS,
    )
