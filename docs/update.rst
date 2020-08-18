.. _update:

Updating student repositories (the ``update`` command)
******************************************************
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

    $ repobee update -a task-1 -s slarse glennol glassey
    [INFO] Cloning into master repos ...
    [INFO] Cloning into https://some-enterprise-host/repobee-demo/task-1
    [INFO] Pushing files to student repos ...
    [INFO] Pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/slarse-task-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glennol-task-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glassey-task-1 master
    [INFO] Done!

That's all there is to it for this super simple case. But what if ``glassey`` had
started working on ``glassey-task-1``?

.. note::

    Here, ``-s slarse glennol glassey`` was used to directly specify student usernames on
    the command line, instead of pointing to a students file with ``--sf
    students.txt``. All commands that require you to specify student usernames
    can be used with either the ``-s|--students`` or the ``--sf|--students-file``
    options.

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

    $ repobee update -a task-1 -s slarse glennol glassey -i issue.md
    [INFO] Cloning into master repos ...
    [INFO] Cloning into https://some-enterprise-host/repobee-demo/task-1
    [INFO] Pushing files to student repos ...
    [INFO] Pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/slarse-task-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glennol-task-1 master
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...
    [INFO] Pushing, attempt 2/3
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...
    [INFO] Pushing, attempt 3/3
    [ERROR] Failed to push to https://some-enterprise-host/repobee-demo/glassey-task-1
    return code: 128
    fatal: repository 'https://some-enterprise-host/repobee-demo/glassey-task-1/' not found
    [WARNING] 1 pushes failed ...
    [INFO] Opening issue in repos to which push failed
    [INFO] Opened issue glassey-task-1/#1-'Nice title'
    [INFO] Done!

Note that RepoBee tries to push 3 times before finally giving up and opening an
issue, as a failed push could be due to any number of reasons, such as
connection issues and misaligned planets.

.. note::

    If you forget to specify the ``-i|--issue`` argument and get a rejection,
    you may simply rerun ``update`` and add it. All updated repos will
    simply be listed as ``up-to-date`` (which is a successful update!), and the
    rejecting repos will still reject the push. However, be careful not to run
    ``update`` with ``-i`` multiple times, as it will then open multiple issues.
