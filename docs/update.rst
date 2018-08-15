.. _update:

Updating Student Repositories (the ``update`` command)
******************************************************
Sometimes, we find ourselves in situations where it is necessary to push
updates to student repositories after they have been published. As long as
students have not started working on their repos, this is fairly simple:
just push the new files to all of the related student repos. However, if
students have started working on their repos, then we have a problem.
Let's start out with the easy case where no students have worked on their
repos.

Scenario 1: Repos are Unchanged
-------------------------------
Let's say that we've updated ``master-repo-1``, and that users ``spam``,
``ham`` and ``eggs`` should get the updates. Then, we simply run
``update`` like this:

.. code-block:: bash

    $ gits_pet update -mn master-repo-1 -s spam eggs ham
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: gits-pet-demo
       
    [INFO] cloning into master repos ...
    [INFO] cloning into https://some-enterprise-host/gits-pet-demo/master-repo-1
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/spam-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/eggs-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/ham-master-repo-1 master
    [INFO] done!

That's all there is to it for this super simple case. But what if ``ham`` had
started working on ``ham-master-repo-1``?

.. note::
    
    Here, ``-s spam eggs ham`` was used to directly specify student usernames on
    the command line, instead of pointing to a students file with ``-sf
    students.txt``. All commands that require you to specify student usernames
    can be used with either the ``-s|--students`` or the ``-sf|--students-file``
    options.

Scenario 2: At Least 1 Repo Altered
-----------------------------------
Let's assume now that ``ham`` has started working on the repo. Since we do not
``force`` pushes (that would be irresponsible!) to the student repos, the
push to ``ham-master-repo-1`` will be rejected. This is good, we don't want to
overwrite a student's progress because we messed up with the original
repository. There are a number of things one *could* do in this situation, but
in ``gits_pet``, we opted for a very simple solution: open an issue in the
student's repo that explains the situation.

.. important::
    
    If we don't specify an issue to ``gits_pet update``, rejected pushes will
    simply be ignored.

So, let's first create that issue. It should be a Markdown-formatted file, and
the **first line in the file will be used as the title**. Here's an example
file called ``issue.md``.

.. code-block:: none

    This is a nice title

    ### Sorry, we messed up!
    There are some grave issues with your repo, and since you've pushed to the
    repo, you need to apply these patches yourself.

    <EXPLAIN CHANGES>

Something like that. If the students have used ``git`` for a while, it may be
enough to include the ouptut from ``git diff``, but for less experienced
students, plain text is more helpful. Now it's just a matter of using
``gits_pet update`` and including ``issue.md`` with the ``-i|--issue`` argument.

.. code-block:: bash

    $ gits_pet update -mn master-repo-1 -s spam eggs ham -i issue.md 
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: gits-pet-demo
       
    [INFO] cloning into master repos ...
    [INFO] cloning into https://some-enterprise-host/gits-pet-demo/master-repo-1
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/spam-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/eggs-master-repo-1 master
    [ERROR] Failed to push to https://some-enterprise-host/gits-pet-demo/ham-master-repo-1
    [WARNING] 1 pushes failed ...
    [INFO] pushing, attempt 2/3
    [ERROR] Failed to push to https://some-enterprise-host/gits-pet-demo/ham-master-repo-1
    [WARNING] 1 pushes failed ...
    [INFO] pushing, attempt 3/3
    [ERROR] Failed to push to https://some-enterprise-host/gits-pet-demo/ham-master-repo-1
    [WARNING] 1 pushes failed ...
    [INFO] Opening issue in repos to which push failed
    [INFO] Opened issue ham-master-repo-1/#1-'Nice title'
    [INFO] done!

Note that ``gits_pet`` tries to push 3 times before finally giving up and
opening an issue. This is because pushes can fail for other reasons than
rejections, such as timeouts and other network errors.

.. note::

    If you forget to specify the ``-i|--issue`` argument and get a rejection,
    you may simply rerun ``update`` and add it. All updated repos will
    simply be listed as ``up-to-date``, and the rejecting repos will still
    reject the push! However, be careful not to run ``update`` with ``-i``
    multiple times, as it will then open the same issue multiple times.
