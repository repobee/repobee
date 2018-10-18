Opening and Closing issues (the ``open-issues`` and ``close-issues`` commands)
****************************************************************************
Sometimes, the best way to handle an error in a repo is to simply notify
affected students about it. This is especially true if the due date for the
assignment is rapidly approaching, and most students have already started
modifying their repositories. Therefore, ``repomate`` provides the
``open-issues`` command, which can open issues in bulk. When the time is right
(perhaps after the deadline has passed), issues can be closed with the
``close-issues`` command.

.. _open:

Opening Issues
--------------
The ``open-issues`` command is very simple. Before we use it, however, we need
to write a Markdown-formatted issue. Just like with the ``update`` command, the
**first line of the file is the title**. Here is ``issue.md``:

.. code-block:: none

    An important announcement

    ### Dear students
    I have this important announcement to make.

    Regards,
    _The Announcer_

Awesome, that's an excellent issue. Let's open it in the ``master-repo-2`` repo
for our dear students ``spam``, ``eggs`` and ``ham``, who are listed in the
``students.txt`` file (see :ref:`setup`).

.. code-block:: bash

    $ repomate open-issues -mn master-repo-2 -sf students.txt -i issue.md 
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] Opened issue spam-master-repo-2/#1-'An important announcement'
    [INFO] Opened issue eggs-master-repo-2/#1-'An important announcement'
    [INFO] Opened issue ham-master-repo-2/#1-'An important announcement'
 
From the output, we can read that in each of the repos, an issue with the title
``An important announcement`` was opened as issue nr 1 (``#1``). The number
isn't that important, it's mostly good to note that the title was fetched
correctly. And that's it! Neat, right?

Closing Issues
--------------
Now that the deadline has passed for ``master-repo-2``, we want to close the
issues opened in open_. The ``close-issues`` command takes a *regex* that runs
against titles. All issues with matching titles are closed. While you *can*
make this really difficult, closing all issues with the title ``An important
announcement`` is simple: we provide the regex ``\AAn important announcement\Z``.

.. code-block:: bash

    $ repomate close-issues -mn master-repo-2 -sf students.txt -r '\AAn important announcement\Z'
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] closed issue spam-master-repo-2/#1-'An important announcement'
    [INFO] closed issue eggs-master-repo-2/#1-'An important announcement'
    [INFO] closed issue ham-master-repo-2/#1-'An important announcement'

And there we go, easy as pie!

.. note::

    Enclosing a regex expression in ``\A`` and ``\Z`` means that it must match
    from the start of the string to the end of the string. So, the regex used here
    *will* match the title ``An important announcement``, but it will *not*
    match e.g.  ``An important anouncement and lunch`` or ``Hey An important
    announcement``. In other words, it matches exactly the title ``An important
    announcement``, and nothing else. Not even an extra space or linebreak is
    allowed.

Listing Issues
--------------
It can often be interesting to check what issues exist in a set of repos,
especially so if you're a teaching assistant who just doesn't want to leave your
trusty terminal. This is where the ``list-issues`` command comes into play.
Typically, we are only interested in open issues, and can then use list
issues like so:

.. code-block:: bash

    $ repomate list-issues -mn master-repo-2 -sf students.txt
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] spam-master-repo-2/#1:  Grading Criteria created 2018-09-12 18:20:56 by glassey
    [INFO] eggs-master-repo-2/#1:  Grading Criteria created 2018-09-12 18:20:56 by glassey
    [INFO] ham-master-repo-2/#1:   Grading Criteria created 2018-09-12 18:20:56 by glassey

So, just grading critera issues posted by the user ``glassey``. What happened to
the important announcements? Well, they are closed. If we want to se closed
issues, we must specifically say so with the ``--closed`` argument.

.. code-block:: bash

    $ repomate list-issues -mn master-repo-2 -sf students.txt --closed
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] spam-master-repo-2/#2:  An important announcement created 2018-09-17 17:46:43 by slarse
    [INFO] eggs-master-repo-2/#2:  An important announcement created 2018-09-17 17:46:43 by slarse
    [INFO] ham-master-repo-2/#2:   An important announcement created 2018-09-17 17:46:43 by slarse

Other interesting arguments include ``--all`` for both open and closed issues,
``--show-body`` for showing the body of each issue, and ``--author <username>``
for filtering by author. There's not much more to it, see ``repomate list-issues
-h`` for complete and up-to-date information on usage!
