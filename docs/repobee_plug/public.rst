.. _public api:

Public API
**********
All of the public functions and classes of ``repobee-plug`` can be imported
from the top-level package ``repobee_plug``. Only this API is stable, the
internal modules currently are not. The recommended way to use ``repobee_plug``
is to import it either as is, or alias it to ``plug``. Typically, I do the
latter.

.. code-block:: python
    :caption: Example usage of repobee-plug

    import repobee_plug as plug

    def act(path, api):
        result = plug.Result(
            name="hello",
            msg="Hello, world!",
            status=plug.Status.SUCCESS,
        )
        return result

    @plug.repobee_hook
    def clone_task():
        """A hello world clone task."""
        return plug.Task(act=act)

Hook functions
==============
There are two parts to hook functions in RepoBee: the specifications of the
hook functions, and the implementation markers to signify that you have
(attempted) to implement a hook.

Implementation markers
----------------------
There are two ways to mark a function as a hook implementation: with the
``repobee_hook`` decorator or using the ``Plugin`` class.

.. autodecorator:: repobee_plug.repobee_hook

.. autoclass:: repobee_plug.Plugin
    :members:

.. _exthooks api:

Extension hooks
---------------

.. important::

    The hook function specifications are part of the public API for
    documentation purposes only. You should not import or use these function in
    any way, but only implement them as described in
    :ref:`implementing hooks`.

.. automodule:: repobee_plug._exthooks
    :noindex:
    :members:

.. _corehooks api:

Core hooks
----------

.. important::

    The hook function specifications are part of the public API for
    documentation purposes only. You should not import or use these function in
    any way, but only implement them as described in
    :ref:`implementing hooks`.

.. automodule:: repobee_plug._corehooks
    :noindex:
    :members:

API Wrappers
============
The API wrappers in ``repobee-plug`` provide a level of abstraction from the
the underlying platform API (e.g. GitHub or GitLab), and allows RepoBee to work
with different platforms. To fully support a new platform, the
:py:class:`~repobee_plug.API` must be subclassed an all of its functions
implemented. It is possible to support a subset of the functionality as well,
but you will need to look into the RepoBee implementation to see which
API methods are required for which commands.

.. autoclass:: repobee_plug.Team
    :members:

.. autoclass:: repobee_plug.TeamPermission
    :members:

.. autoclass:: repobee_plug.Issue
    :members:

.. autoclass:: repobee_plug.IssueState
    :members:
    :inherited-members:

.. autoclass:: repobee_plug.Repo
    :members:

.. autoclass:: repobee_plug.API
    :members:
    :inherited-members:

Containers
==========
The containers in ``repobee-plug`` are immutable classes for storing data.
Probably the most important containers are the
:py:class:`~repobee_plug.Result` and the :py:class:`~repobee_plug.Task`
classes.

.. autoclass:: repobee_plug.Result
    :members:

.. autoclass:: repobee_plug.Task
    :members:

.. autoclass:: repobee_plug.Deprecation
    :members:

.. autoclass:: repobee_plug.Status
    :members:

.. autoclass:: repobee_plug.ExtensionCommand
    :members:

.. autoclass:: repobee_plug.ExtensionParser
    :members:
    :inherited-members:

.. autoclass:: repobee_plug.ReviewAllocation
    :members:

.. autoclass:: repobee_plug.Review
    :members:

Helpers
=======
``repobee-plug`` defines various helper functions and classes for use in both
RepoBee core and in plugins. These vary from generating repo names, to handling
deprecation, to mapping key data structures from and to JSON.

.. autofunction:: repobee_plug.json_to_result_mapping

.. autofunction:: repobee_plug.result_mapping_to_json

.. autofunction:: repobee_plug.generate_repo_name

.. autofunction:: repobee_plug.generate_repo_names

.. autofunction:: repobee_plug.generate_review_team_name

.. autodecorator:: repobee_plug.deprecate

.. autofunction:: repobee_plug.deprecated_hooks

Exceptions
==========

.. autoexception:: repobee_plug.PlugError
    :members:

.. autoexception:: repobee_plug.ExtensionCommandError
    :members:

.. autoexception:: repobee_plug.HookNameError
    :members:
