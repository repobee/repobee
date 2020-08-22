.. _groups:

Group assignments
*****************

RepoBee supports group assignments such that multiple students are assigned to
the same student repositories. To put students in a group, they need to be
entered on the same line in the students file, separated by spaces. This is the
only way to group students, the ``-s`` option on the command line does not
support groups. As an example, if ``glassey`` and ``slarse`` should be in one group,
and ``glennol`` solo, the following students file would work:

.. code-block:: bash

   glassey slarse
   glennol

There is no difference in using RepoBee with student groups in the student
file. For example, running the setup command from :ref:`setup` would look just
the same:

.. code-block:: bash

    $ repobee repos setup -a task-1 task-2 --sf students.txt

The naming convention for group repos is as follows:
``<student-1>-<student-2>-[...]-<template-repo-name>``, where the student names
are sorted lexicographically. The associated teams follow the same convention,
but without the trailing ``-<template-repo-name>``. And that is all you need
to know to start doing group assignments!

.. warning::

   The naming scheme has a weakness: it can create fairly long names, and
   GitHub has a hard limit for repo names at 100 characters. RepoBee will
   therefore crash (on purpose) if a Team or repo name exceeds 100 characters.
   There is no workaround for this problem at the moment, as we've never
   actually encountered it. Please make us aware if you encounter it and we
   will make an effort to resolve the issue.
