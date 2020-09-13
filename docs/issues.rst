Managing issues (the ``issues`` category)
*****************************************

The ``issues`` category of commands allows you to manage the issue trackers of
the student repositories. The currently available core actions are ``open``,
``close`` and ``list``, which achieve about what you'd expect.

.. _open:

Opening Issues (the ``open`` action)
====================================
The ``issues open`` command is very simple. Before we use it, however, we need
to write a Markdown-formatted issue. Just like with the ``update`` command (see
:ref:`update`), the **first line of the file is the title**. Here is
``issue.md``:

.. code-block:: none
   :caption: issue.md

   An important announcement

   ### Dear students
   I have this important announcement to make.

   Regards,
   _The Announcer_

Awesome, that's an excellent issue. Let's open it in the ``task-2`` repo
for our dear students ``slarse``, ``glennol`` and ``glassey``, who are listed in the
``students.txt`` file (see :ref:`setup`).

.. code-block:: bash

    $ repobee issues open --assignments task-2 --students-file students.txt -i issue.md
    Opened issue slarse-task-2/#1-'An important announcement'
    Opened issue glennol-task-2/#1-'An important announcement'
    Opened issue glassey-task-2/#1-'An important announcement'

From the output, we can read that in each of the repos, an issue with the title
``An important announcement`` was opened as issue nr 1 (``#1``). The number
isn't that important, it's mostly good to note that the title was fetched
correctly. And that's it! Neat, right?

.. _close:

Closing Issues (the ``close`` action)
=====================================
Now that the deadline has passed for ``task-2``, we want to close the
issues opened in open_. The ``close-issues`` command takes a *regex* that runs
against titles. All issues with matching titles are closed. While you *can*
make this really difficult, closing all issues with the title ``An important
announcement`` is simple: we provide the regex ``\AAn important announcement\Z``.

.. code-block:: bash

    $ repobee issues close -a task-2 --sf students.txt -r '\AAn important announcement\Z'
    [INFO] Closed issue slarse-task-2/#1-'An important announcement'
    [INFO] Closed issue glennol-task-2/#1-'An important announcement'
    [INFO] Closed issue glassey-task-2/#1-'An important announcement'

And there we go, easy as pie!

.. note::

    Enclosing a regex expression in ``\A`` and ``\Z`` means that it must match
    from the start of the string to the end of the string. So, the regex used here
    *will* match the title ``An important announcement``, but it will *not*
    match e.g.  ``An important anouncement and lunch`` or ``Hey An important
    announcement``. In other words, it matches exactly the title ``An important
    announcement``, and nothing else. Not even an extra space or linebreak is
    allowed.

Listing Issues (the ``list`` action)
====================================
It can often be interesting to check what issues exist in a set of repos,
especially so if you're a teaching assistant who just doesn't want to leave your
trusty terminal. This is where the ``issues list`` command comes into play.
Typically, we are only interested in open issues, and can then use list
issues like so:

.. code-block:: bash

    $ repobee issues list -a task-2 --sf students.txt
    [INFO] slarse-task-2/#1:  Grading Criteria created 2018-09-12 18:20:56 by glassey
    [INFO] glennol-task-2/#1:  Grading Criteria created 2018-09-12 18:20:56 by glassey
    [INFO] glassey-task-2/#1:   Grading Criteria created 2018-09-12 18:20:56 by glassey

So, just grading critera issues posted by the user ``glassey``. What happened to
the important announcements? Well, they are closed. If we want to se closed
issues, we must specifically say so with the ``--closed`` argument.

.. code-block:: bash

    $ repobee issues list -a task-2 --sf students.txt --closed
    [INFO] slarse-task-2/#2:  An important announcement created 2018-09-17 17:46:43 by slarse
    [INFO] glennol-task-2/#2:  An important announcement created 2018-09-17 17:46:43 by slarse
    [INFO] glassey-task-2/#2:   An important announcement created 2018-09-17 17:46:43 by slarse

Other interesting arguments include ``--all`` for both open and closed issues,
``--show-body`` for showing the body of each issue, and ``--author <username>``
for filtering by author. There's not much more to it, see ``repobee issues list
-h`` for complete and up-to-date information on usage!
