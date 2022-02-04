"""Wrapper functions for git commands.

.. module:: git
    :synopsis: Wrapper functions for git CLI commands, such as push and clone.
"""

from _repobee.git._push import PushSpec, push  # NOQA

from _repobee.git._fetch import (  # NOQA
    CloneSpec,
    CloneStatus,
    clone,
    clone_student_repos,
    clone_single,
)

from _repobee.git._local import (  # NOQA
    active_branch,
    git_init,
    stash_changes,
    set_gitconfig_options,
)

from _repobee.git._util import is_git_repo  # NOQA
