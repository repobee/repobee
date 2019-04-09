.. _groups:

Group assignments
*****************

.. note::
   
   **New in v1.3.0!** This feature is in beta phase, please report any bugs you
   encounter on the GitHub issue tracker!

.. important::

   The peer review commands (see :ref:`peer review`) do not currently support
   group assignments.

RepoBee supports group assignments such that multiple students are assigned to
the same student repositories. To put students in a group, they need to be
entered on the same line in the students file, separated by spaces. This is the
only way to group students, the ``--s`` option on the command line does not
support groups. As an example, if ``ham`` and ``spam`` should be in one group,
and ``eggs`` solo, the following students file would work:

.. code-block:: bash

   ham spam
   eggs

There is no difference in using RepoBee with student groups in the student
file. For example, running the setup command from :ref:`setup` would then have
the following result:

.. code-block:: bash

    $ repobee setup -mn master-repo-1 master-repo-2 -sf students.txt
    [INFO] cloning into master repos ...
    [INFO] cloning into file:///home/slarse/tmp/master-repo-1
    [INFO] cloning into file:///home/slarse/tmp/master-repo-2
    [INFO] created team eggs
    [INFO] created team ham-spam
    [INFO] adding members eggs to team eggs
    [WARNING] user eggs does not exist
    [INFO] adding members ham, spam to team ham-spam
    [INFO] creating student repos ...
    [INFO] created repobee-demo/eggs-master-repo-1
    [INFO] created repobee-demo/ham-spam-master-repo-1
    [INFO] created repobee-demo/eggs-master-repo-2
    [INFO] created repobee-demo/ham-spam-master-repo-2
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/ham-spam-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/ham-spam-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/eggs-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/eggs-master-repo-1 master

Note the naming convention for group repos:
``<student-1>-<student-2>-[...]-<master-repo-name>``. The associated teams
follow the same convention, but without the trailing ``-<master-repo-name>``.
And that is all you need to know to start doing group assignments!

.. warning::

   The naming scheme has a weakness: it can create fairly long names, and
   GitHub has a hard limit for repo names at 100 characters. RepoBee will
   therefore crash (on purpose) if a Team or repo name exceeds 100 characters.
   There is no workaround for this problem at the moment.
