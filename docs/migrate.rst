.. _migrate:

Migrate repositories into the target (or master) organization (``migrate`` command)
***********************************************************************************
Migrating repositories from one organization to another can be useful in a few
cases. You may have repos that should be accessible to students and need to be
moved across course rounds, or you might be storing your master repos in the
target organization and need to migrate them for each new course round. To
migrate repos into the target organization, they need to be either:

* Local in the current working directory, and specified by name.

or

* Somewhere in the target GitHub instance, and specified by URL.

Assuming we have the repos ``master-repo-1`` and ``master-repo-2`` in the
current working directory (i.e. local repos), all we have to do is this:

.. code-block:: bash

    $ repobee migrate -mn master-repo-1 master-repo-2
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] created repobee-demo/master-repo-1
    [INFO] created repobee-demo/master-repo-2
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/master-repo-2 master
    [INFO] done!

.. important::

    If you want to use this command to migrate repos into a master organization,
    you must specify it with the ``--org-name`` option here (instead of the
    ``--master-org-name``).

What happens here is pretty straightforward, except for the local repos being
cloned, which is an implementation detail that does not need to be thought
further of. Note that only the defualt branch is actually migrated, and pushed
to ``master`` in the new repo. local repos are pushed to the ``master`` branch
of the remote repo. Migrating several branches is something that we've never
had a need to do, but if you do, please open an issue on GitHub with a feature
request. ``migrate`` is perfectly safe to run several times, in case you think
you missed something, or need to update repos. Running the same thing again
without changing the local repos yields the following output:

.. code-block:: bash

    $ repobee migrate -mn master-repo-1 master-repo-2
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] repobee-demo/master-repo-1 already exists
    [INFO] repobee-demo/master-repo-2 already exists
    [INFO] pushing, attempt 1/3
    [INFO] https://some-enterprise-host/repobee-demo/master-repo-1 master is up-to-date
    [INFO] https://some-enterprise-host/repobee-demo/master-repo-2 master is up-to-date
    [INFO] done!

In fact, all RepoBee commands that deal with pushing to or cloning from
repos in some way are safe to run over and over. This is mostly because of
how Git works, and has little to do with RepoBee itself.

.. note::

    The ``migrate`` command can also be used to migrate repos from somewhere
    on the GitHub instance into the target organization. To do this, use the
    ``-mu`` option and provide the urls, instead of ``-mn`` with local paths.
    For example, given a repo at
    ``https://some-enterprise-host/other-org/master-repo-1``, it can be
    migrated into ``repobee-demo`` by typing

    .. code-block:: bash

        $ repobee migrate -mu https://some-enterprise-host/other-org/master-repo-1
