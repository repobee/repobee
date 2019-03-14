.. _migrate:

Migrate master repositories into the target (or master) organization (``migrate`` command)
******************************************************************************************
This step sounds complicated, but it's actually very easy, and can be performed
with a single Repomate command. There is however a pre-requisite that must
be fulfilled. You must either

* Have local copies of your master repos.

or

* Have all master repos in the same GitHub instance as your target organization.

Assuming we have the repos ``master-repo-1`` and ``master-repo-2`` in the
current working directory (i.e. local repos), all we have to do is this:

.. code-block:: bash

    $ repomate migrate -mn master-repo-1 master-repo-2
    [INFO] created team master_repos
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] created repomate-demo/master-repo-1
    [INFO] created repomate-demo/master-repo-2
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/master-repo-2 master
    [INFO] done!

.. important::

    If you want to use this command to migrate repos into a master organization,
    you must specify it with the ``--org-name`` option here (instead of the
    ``--master-org-name``).

There are a few things to note here. First of all, the team ``master_repos`` is
created. This only happens the first time ``migrate`` is run on a new
organization. As the name suggests, this team houses all of the master repos.
Each master repo that is migrated with the ``migrate`` command is added to this
team, so they can easily be found at a later time. It may also be confusing that
the local repos are being cloned (into a temporary directory). This is simply
an implementation detail that does not need much thinking about. Finally, the
local repos are pushed to the ``master`` branch of the remote repo. This command
is perfectly safe to run several times, in case you think you missed something.
Running the same thing again yields the following output:

.. code-block:: bash

    $ repomate migrate -mn master-repo-1 master-repo-2
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] repomate-demo/master-repo-1 already exists
    [INFO] repomate-demo/master-repo-2 already exists
    [INFO] pushing, attempt 1/3
    [INFO] https://some-enterprise-host/repomate-demo/master-repo-1 master is up-to-date
    [INFO] https://some-enterprise-host/repomate-demo/master-repo-2 master is up-to-date
    [INFO] done!

In fact, all Repomate commands that deal with pushing to or cloning from
repos in some way are safe to run over and over. This is mostly because of
how git works, and has little to do with Repomate itself. Now that
our master repos are migrated, we can move on to setting up the student repos!

.. note::

    The ``migrate`` command can also be used to migrate repos from somewhere
    on the GitHub instance into the target organization. To do this, use the
    ``-mu`` option and provide the urls, instead of ``-mn`` with local paths.
    For example, given a repo at
    ``https://some-enterprise-host/other-org/master-repo-1``, it can be
    migrated into ``repomate-demo`` by typing

    .. code-block:: bash

        $ repomate migrate -mu https://some-enterprise-host/other-org/master-repo-1
