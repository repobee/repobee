.. _migrate:

Migrate repositories into the target (or master) organization (``migrate`` command)
***********************************************************************************
Migrating repositories into an organization can be useful in a few cases. You
may have repos that should be accessible to students and need to be moved
across course rounds, or you might be storing your master repos in the target
organization and need to migrate them for each new course round. To migrate
repos into the target organization, they must be local on disc. Assuming we
have the repos ``task-1`` and ``task-2`` in the current working
directory (i.e. local repos), all we have to do is this:

.. note::

   Prior to v1.4.0, the ``migrate`` command also accepted urls with the
   ``-mu`` option. This functionality was abruptly removed due to
   implementation issues, and is unlikely to appear again because of its
   limited use.

.. code-block:: bash

    $ repobee migrate -a task-1 task-2
    [INFO] cloning into file:///some/directory/path/task-1
    [INFO] cloning into file:///some/directory/path/task-2
    [INFO] created repobee-demo/task-1
    [INFO] created repobee-demo/task-2
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/task-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/task-2 master
    [INFO] done!

.. important::

    If you want to use this command to migrate repos into a master organization,
    you must specify it with the ``--org-name`` option here (instead of the
    ``--master-org-name``).

What happens here is pretty straightforward, except for the local repos being
cloned, which is an implementation detail that does not need to be thought
further of. Note that only the defualt branch is actually migrated, and pushed
to ``master`` in the new repo. Local repos are pushed to the ``master`` branch
of the remote repo. Migrating several branches is something that we've never
had a need to do, but if you do, please `open an issue on GitHub
<https://github.com/repobee/repobee/issues/new>`_ with a feature request.
``migrate`` is perfectly safe to run several times, in case you think you
missed something, or need to update repos. Running the same thing again without
changing the local repos yields the following output:

.. code-block:: bash

    $ repobee migrate -a task-1 task-2
    [INFO] cloning into file:///some/directory/path/task-1
    [INFO] cloning into file:///some/directory/path/task-2
    [INFO] repobee-demo/task-1 already exists
    [INFO] repobee-demo/task-2 already exists
    [INFO] pushing, attempt 1/3
    [INFO] https://some-enterprise-host/repobee-demo/task-1 master is up-to-date
    [INFO] https://some-enterprise-host/repobee-demo/task-2 master is up-to-date
    [INFO] done!

In fact, all RepoBee commands that deal with pushing to or cloning from
repos in some way are safe to run over and over. This is mostly because of
how Git works, and has little to do with RepoBee itself.
