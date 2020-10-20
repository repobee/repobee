.. _repos category:

Managing student repositories (the ``repos`` category)
******************************************************

The ``repos`` category of commands allows you to manage student repositories
with a few simple, high-level operations. Each action in the ``repos`` category
is more or less independent.

.. hint::

    For an up-to-date listing of all ``repos`` actions, run ``repobee repos
    -h``.

.. _setup:

Set up student repositories (the ``setup`` action)
==================================================

Now that the template repos are set up, it's time to create the student repos.
While student usernames *can* be specified on the command line, it's often
convenient to have them written down in a file instead. Let's pretend like we
have the single-student team ``students.txt`` file from :ref:`config` at our
disposal.

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

    $ repobee repos update --assignments task-1 --students slarse glennol glassey
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

    If you don't specify an issue to ``repos update``, rejected pushes will
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

    $ repobee repos update --assignments task-1 --students slarse glennol glassey -i issue.md
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

Cloning Repos in Bulk (the ``clone`` action)
============================================

It can at times be beneficial to be able to clone a bunch of student repos
at the same time. It could for example be prudent to do this slightly after
a deadline, as timestamps in a ``git`` commit can easily be altered (and are
therefore not particularly trustworthy). Whatever your reason may be, it's
very simple using the ``clone`` command. Again, assume that we have the
``students.txt`` file from :ref:`setup`, and that we want to clone all student
repos based on ``task-1`` and ``task-2``.

.. code-block:: bash

    $ repobee repos clone -a task-1 task-2 --sf students.txt
    [INFO] cloning into student repos ...
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/slarse-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glassey-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glassey-task-2
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glennol-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/slarse-task-2
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glennol-task-2

Splendid! That's really all there is to the basic functionality, the repos
should now be in your current working directory. There is also a possibility to
run automated tasks on cloned repos, such as running test suites or linters. If
you're not satisfied with the tasks on offer, you can define your own. Read more
about it in the :ref:`plugins` section.

.. note::

   `For security reasons
   <https://github.blog/2012-09-21-easier-builds-and-deployments-using-git-over-https-and-oauth/>`_,
   RepoBee doesn't actually use ``git clone`` to clone repositories. Instead,
   RepoBee clones by initializing the repository and running ``git pull``. The
   practical implication is that you can't simply enter a repository that's
   been cloned with RepoBee and run ``git pull`` to fetch updates. You will
   have to run ``repos clone`` again in a different directory to fetch any
   updates students have made, alternatively simply delete to particular
   repositories you want to clone again and then run ``repos clone``.

.. _migrate:

Migrate repositories into the target (or template) organization (the ``migrate`` action)
========================================================================================

Migrating repositories into an organization can be useful in a few cases. You
may have repos that should be accessible to students and need to be moved
across course rounds, or you might be storing your template repos in the target
organization and need to migrate them for each new course round. To migrate
repos into the target organization, they must be local on disc. Assuming we
have the repos ``task-1`` and ``task-2`` in the current working
directory (i.e. local repos), all we have to do is this:

.. code-block:: bash

    $ repobee repos migrate --assignments task-1 task-2

.. note::

    It may seem a bit odd that the ``--assignments`` option is used to specify
    the repos to migrate. This is an implementation detail that makes it easier
    to handle the command, but may be changed in the future for better
    usability.

.. important::

    If you want to use this command to migrate repos into a template
    organization, you must specify it with the ``--org-name`` option here
    (instead of the ``--template-org-name``).

Only the defualt branch is actually migrated, and is pushed to that same
default branch in the new repo.  Migrating several branches is something that
we've never had a need to do, but if you do, please `open an issue on GitHub
<https://github.com/repobee/repobee/issues/new>`_ with a feature request.
``migrate`` is perfectly safe to run several times, in case you think you
missed something, or need to update repos. In fact, all RepoBee commands that
deal with pushing to or cloning from repos in some way are safe to run over and
over. This is mostly because of how Git works, and has little to do with
RepoBee itself.
