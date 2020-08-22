.. _repos category:

Managing student repositories (the ``repos`` category)
******************************************************

The ``repos`` category of commands allows you to manage student repositories
with a few simple, high-level operations. Each action in the ``repos`` category
is more or less independent.

.. _setup:

Set up student repositories (the ``setup`` action)
==================================================

Now that the template repos are set up, it's time to create the student repos.
While student usernames *can* be specified on the command line, it's often
convenient to have them written down in a file instead. Let's pretend I have
three students with usernames ``slarse``, ``glassey`` and ``glennol``. I'll
simply create a file called ``students.txt`` and type each username on a
separate line.

.. code-block:: bash
   :caption: students.txt

    slarse
    glassey
    glennol

.. note::

   It is possible to specify groups of students to get access to the same repos
   by putting multiple usernames on the same line, separated by spaces. For
   example, the following file will put `slarse` and `glassey` in the same
   group.

   .. code-block:: bash

      slarse glassey
      glennol

   See :ref:`groups` for details.

An absolute file path to this file can be added to the config file with the
``students_file`` option (see :ref:`config`). If you manage multiple sets of
students, this probably isn't useful to you, but if you always have a single set
of students to manage it might be.

Now, what we want to accomplish is to create one copy of each template repo for
each student. The repo names will be on the form
``<username>-<template-repo-name>``, guaranteeing their uniqueness. Each student
will also be added to a team (which bears the same name as the student's user),
and it is the team that is allowed access to the student's repos, not the
student's actual user. That all sounded fairly complex, but again, it's as
simple as issuing a single command with RepoBee.

.. code-block:: bash

    $ repobee repos setup --assignments task-1 task-2 --students-file students.txt
    # you will see progress bars here to show how far along the setup process is
    [WARNING] user glennol does not exist

.. note::

   If you have specified the ``students_file`` option in the config file, then
   you don't need to specify ``--sf students.txt`` on the command line. Remember
   also that options specified on the command line always take precedence over
   those in the configuration file, so you can override the default students
   file if you wish by specifying ``--sf``..

Note that there was a ``[WARNING]`` message for the username ``glennol``: the
user does not exist. At KTH, this is common, as many (sometimes most) first-time
students will not have created their GitHub accounts until sometime after the
course starts. These students will still have their repos created, but the users
need to be added to their teams at a later time (to do this, simply run the
``repos setup`` command again for these students, once they have created
accounts).  This is one reason why we use teams for access privileges: it's easy
to set everything up even when the students have yet to create their accounts
(given that their usernames are pre-determined).

And that's it for setting up the course, the organization is primed and the
students should have access to their repositories!

.. _update:

Updating student repositories (the ``update`` action)
=====================================================

Sometimes, we find ourselves in situations where it is necessary to push
updates to student repositories after they have been published. As long as
students have not started working on their repos, this is fairly simple:
just push the new files to all of the related student repos. However, if
students have started working on their repos, then we have a problem.
Let's start out with the easy case where no students have worked on their
repos.

Scenario 1: Repos are unchanged
-------------------------------

Let's say that we've updated ``task-1``, and that users ``slarse``,
``glassey`` and ``glennol`` should get the updates. Then, we simply run
``update`` like this:

.. code-block:: bash

    $ repobee update --assignments task-1 --students slarse glennol glassey
    # again, there will be progress bars here

That's all there is to it for this super simple case. But what if ``glassey`` had
started working on ``glassey-task-1``?

.. note::

    Here, ``--students slarse glennol glassey`` was used to directly specify
    student usernames on the command line, instead of pointing to a students
    file with ``--sf students.txt``. All commands that require you to specify
    student usernames can be used with either the ``-s|--students`` or the
    ``--sf|--students-file`` options.

Scenario 2: At least 1 repo altered
-----------------------------------

Let's assume now that ``glassey`` has started working on the repo. Since we do not
force pushes to the student repos, the push to ``glassey-task-1`` will be
rejected. This is good, we don't want to overwrite a student's progress because
we messed up with the original repository. There are a number of things one
*could* do in this situation, but in RepoBee, we opted for a very simple
solution: open an issue in the student's repo that explains the situation.

.. important::

    If you don't specify an issue to ``repobee update``, rejected pushes will
    simply be ignored.

So, let's first create that issue. It should be a Markdown-formatted file, and
the **first line in the file will be used as the title**. Here's an example
file called ``issue.md``.

.. code-block:: none
   :caption: issue.md

   This is a nice title

   ### Sorry, we messed up!
   There are some grave issues with your repo, and since you've pushed to the
   repo, you need to apply these patches yourself.

   <EXPLAIN CHANGES>

Something like that. If the students have used ``git`` for a while, it may be
enough to include the ouptut from ``git diff``, but for less experienced
students, plain text is more helpful. Now it's just a matter of using
``repobee update`` and including ``issue.md`` with the ``-i|--issue`` argument.

.. code-block:: bash

    $ repobee update --assignments task-1 --students slarse glennol glassey -i issue.md
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...

Note that RepoBee tries to push 3 times before finally giving up and opening an
issue, as a failed push could be due to any number of reasons, such as
connection issues and misaligned planets.

.. note::

    If you forget to specify the ``-i|--issue`` argument and get a rejection,
    you may simply rerun ``update`` and add it. All updated repos will
    simply be listed as ``up-to-date`` (which is a successful update!), and the
    rejecting repos will still reject the push. However, be careful not to run
    ``update`` with ``-i`` multiple times, as it will then open multiple issues.
