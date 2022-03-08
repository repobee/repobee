.. _peer review:

Managing peer review (the ``reviews`` category)
***********************************************

Peer reviewing is an important part of a programming curriculum, so of course
RepoBee facilitates this! Like much of the other functionality in RepoBee, the
peer review functionality is built around indirect access through teams with
limited access privileges. In short, every student repo up for review gets an
associated peer review team generated, which has ``pull`` access to the repo.
Each student then gets added to ``0 < N < num_students`` peer review teams, and
are to open a peer review issue in the associated repos. This is at least the
the default. See :ref:`review allocation algorithm` for other available review
allocation schemes.

.. _assign reviews:

Getting started with peer reviews (the ``assign`` action)
=========================================================

The bulk of the work is performed by the ``reviews assign``. Most of its
arguments it has in common with the other commands of RepoBee. The only
non-standard arguments are ``--issue`` and ``--num-reviews``, the former of
which we've actually already seen in the ``issues open`` command (see
:ref:`open`). We will assume that both ``--base-url`` and ``--org-name`` are
already configured (if you don't know what this means, have a look at
:ref:`config`). Thus, the only things we must specify are
``--students/--students-file`` and ``--num-reviews`` (``--issue`` is optional,
more on that later). Let's make a minimal call with the ``assign`` action, and
then inspect the log output to figure out what happened. Recall that
``students.txt`` lists our three favorite students slarse, glassey and glennol
(see :ref:`setup`).

.. code-block:: bash

    $ repobee reviews assign -a task-1 --sf students.txt --num-reviews 2


    # Output nabbed from the log file, this will not appear on stdout

    # step 1
    [INFO] Created team slarse-task-1-review
    [INFO] Created team glennol-task-1-review
    [INFO] Created team glassey-task-1-review
    # step 2
    [INFO] Adding members glennol, glassey to team slarse-task-1-review
    [INFO] Adding members glassey, slarse to team glennol-task-1-review
    [INFO] Adding members slarse, glennol to team glassey-task-1-review
    # steps 3 and 4, interleaved
    [INFO] Opened issue glennol-task-1/#1-'Peer review'
    [INFO] Adding team glennol-task-1-review to repo glennol-task-1 with 'pull' permission
    [INFO] Opened issue glassey-task-1/#2-'Peer review'
    [INFO] Adding team glassey-task-1-review to repo glassey-task-1 with 'pull' permission
    [INFO] Opened issue slarse-task-1/#2-'Peer review'
    [INFO] Adding team slarse-task-1-review to repo slarse-task-1 with 'pull' permission

The following steps were performed:

1. One review team per repo was created (``<student>-task-1-review``).
2. Two students were added to each review team. Note that these allocations are
   _random_. For obvious resons, there can be at most ``num_students-1`` peer
   reviews per repo. So, in this case, we are at the maximum.
3. An issue was opened for each reviewing student in each repo with the title
   ``Peer review (student-name)``, and a body saying something like ``You should peer review
   this repo.``. The review team students were assigned to their respective issue as well
   (although this is not apparent from the logging).
4. The review teams were added to their corresponding repos with ``pull``
   permission. This permission allows members of the team to view the repo and
   open issues, but they can't push to (and therefore can't modify) the repo.

That's it for the basic functionality. The intent is that students should open
an issue in every repo they are to peer review, with a specific title. The issues
can then be searched by title, and the ``check`` action can find which students
have opened issues in the repositories they've been assigned to review.  Now,
let's talk a bit about that ``--issue`` argument.

.. important::

    Assigning peer reviews gives the reviewers read-access to the repos they are
    to review. This means that if you use issues to communicate grades/feedback
    to your students, the reviewers will also see this feedback! It is therefore
    important to remove the peer review teams (see :ref:`purge peer review
    teams`).

Specifying a custom issue
-------------------------

The default issue is really meant to be replaced with something more specific to
the course and assignment. For example, say that there were five tasks in the
``task-1`` repo, and the students should review tasks 2 and 3 based on
some criteria. It would then be beneficial to specify this in the peer review
issue, so we'll write up our own little issue to replace the default one.
Remember that the first line is taken to be the title, in exactly the same way
as issue files are treated in :ref:`open`.

.. code-block:: none

    Review of task-1

    Hello! The students assigned to this issue have been tasked to review this
    repo. Each of you should open _one_ issue with the title `Peer review` and
    the following content:

    ## Task 2
    ### Code style
    Comments on code style, such as readability and general formatting.

    ### Time complexity
    Is the algorithm O(n)? If not, try to figure out what time complexity it is
    and point out what could have been done better.

    ## Task 3
    ### Code style
    Comments on code style, such as readabilty and general formatting.

Assuming the file was saved as ``issue.md``, we can now run the command
specifying the issue like this:

.. code-block:: bash

   $ repobee reviews assign -a task-1 --sf students.txt --num-reviews 2 --issue issue.md

This will have the same effect as last time, but with the custom issue being
opened instead.

.. _reviews check:

Checking review progress (the ``check`` action)
===============================================
The ``check`` action provides a quick and easy way of checking which
students have performed their reviews. You provide it with the same information
that you do for ``assign``, but additionally also provide a regex to match
against issue titles. The command then finds all of the associated review
teams, and checks which students have opened issues with matching titles in
their alloted repositories. Of course, this says *nothing* about the content of
those issues: it only checks that the issues have been opened at all.
``--num-reviews`` is also required here, as it is used as an expected value for
how many reviews each student *should* be assigned to review. It is a simple
but fairly effective way of detecting if students have simply left their review
teams. Here's an example call:

.. code-block:: bash

   $ repobee reviews check -a task-1 --sf students.txt --num-reviews 2 --title-regex '\APeer review\Z'
   reviewer        num done        num remaining   repos remaining
   glennol         0               2               glassey-task-1,slarse-task-1
   slarse          2               0
   glassey         0               2               glennol-task-1,slarse-task-1

The output is color-coded in the terminal, making it easier to parse. We make use
of this when doing peer reviews in a classroom settings, as it allows us to
quickly check which students are done without having to ask them out loud every
five minutes. The next command lets you clean up review teams and thereby
revoke reviewers' read access once reviews are over and done with.

.. hint::

    Use the ``issues list`` command with the ``--title-regex`` (with a regex
    matching the review issue title) and ``--show-body`` options to actually
    check the contents of the students' review issues.

.. _purge peer review teams:

Cleaning up with (then ``end`` action)
======================================

The one downside of using teams for access privileges is that we bloat the
organization with a ton of teams. Once the deadline has passed and all peer
reviews are done, there is little reason to keep them. It can also often be a
good idea to revoke the reviewers' access to reviewed repos if you yourself
plan to provide feedback on the issue tracker, so as not to let the reviewers
see it. Therefore, the ``end`` action can be used to remove all peer review
teams for a given set of student repos, both cleaning up the organization and
revoking reviewers' read access. Let's say that we're completely done with the
peer reviews of ``task-1``, and want to remove the review teams. It's as simple
as:

.. code-block:: bash

    $ repobee reviews end -a task-1 --sf students.txt
    # Progress bars will show how many teams have been deleted thus far

.. warning::

   The ``end`` action *deletes* review allocations created by
   ``assign``.  This is an irreversible action. You cannot run
   ``check`` after running ``end`` for any given set of student repos, and
   there is no functionality for retrieving deleted review allocations. Only
   use ``end`` when reviews are truly done, **and** you have collected what
   results you need. If being able to backup and restore review allocations is
   something you need, please open an issue with a feature request `on the
   issue tracker <https://github.com/repobee/repobee/issues/new>`_.

And that's it, the review teams are gone. If you also want to close the related
issues, you can simply use the ``issues close`` command for that (see
:ref:`close`). The ``end`` action plays one more important role; if you mess
something up when assigning the peer reviews. The next section details how you
can deal with such a scenario.

Messing up and getting back on track
====================================

Let's say you messed something up with allocating the peer reviews. For example,
if you left out a student, there is no easy way to rectify the allocations such
that that student is included. Let's say we did just that, and forgot to include
the student ``cabbage`` in the reviews for ``task-1`` back at
:ref:`assign reviews`. We then do the following:

1. Check if any reviews have already been posted. This can easily be performed
   with ``repobee reviews check -a task-1 --sf students.txt -r '^Peer
   review$' --num-reviews 2`` (assuming the naming conventions were followed!). Take appropriate
   action if you find any reviews already posted (appropriate being anything you
   see fit to alleviate the situation of affected students possibly being
   assigned new repos to review).
2. Delete the review teams with ``repobee reviews end -a task-1
   --sf students.txt``
3. Close all review issues with ``repobee issues close -a task-1 --sf
   students.txt -r '^Review of task-1$'``
4. Create a new ``issue.md`` file apologetically explaining that you messed up:

.. code-block:: none

    Review of task-1 (for real this time!)

    Sorry, I messed up with the allocations previously. Disregard the previous
    allocations (repo access has been revoked anyway).

5. Assign peer reviews again, with the new issue, with ``repobee
   reviews assign -a task-1 --sf students.txt --num-reviews 2
   --issue issue.md``

And that's it! Disaster averted.


.. _review allocation algorithm:

Selecting peer review allocation algorithm
==========================================
The default allocation algorithm is as described in :ref:`peer review`, and is
suitable for when reviewers do not need to interact with the students whom they
review. This is however not always the case, sometimes it is beneficial for
reviewers to to interact with reviewees (is that a word?), especially if the
peer review is done in the classroom. Because of this, RepoBee also
provides a _pairwise_ allocation scheme, which allocates reviews such that
if student ``A`` reviews student ``B``, then student ``B`` reviews student
``A`` (except for an ``A->B->C->A`` kind of deal in one group if there are an
odd amount of students). This implemented as a plugin, so to run with this
scheme, you add ``-p pairwise`` in front of the command.

.. code-block:: bash

    $ repobee -p pairwise reviews assign -a task-1 --sf students.txt

Note that the pairwise algorithm ignores the ``--num-reviews`` argument, and
will issue a warning if this is set (to anything but 1, but you should just not
specify it). For more details on plugins in RepoBee, see :ref:`plugins`.

Double-blind peer review
========================

RepoBee 3.6 adds experimental support for double-blind peer review. The user
experience is not finalized, but the functionality is all there. This section
provides a walkthrough for how to assign double-blind peer review. It assumes
that you've read through the prior sections of the peer review documentation.

Overview
--------

The general idea of the double-blind peer review is to assign reviewers to
review copies of their peers' repositories. The whole procedure is something
like this:

1. ``reviews assign`` Create copies of all student repositories under review and assign reviewers to them

    - The commit history is anonymized

    - The repository name is anonymized

2. ``reviews check`` Verify that students have performed their reviews

3. ``issues list`` Collect reviews from anonymous repos and store them locally

4. ``issues open`` Distribute anonymously submitted reviews to original repositories

    - They are opened with your user account, so as long as reviewers haven't put their names in the reviews they will be anonymous!

5. (Optional) ``reviews end`` Delete repo copies and associated review teams

    - **Always** run ``issues list`` to collect the reviews before running
      ``reviews end``, or all reviews will be lost!


As you may note, this is the same sequence of commands as for no-blind review,
except that ``issues list`` and ``issues open`` are sprinkled into the middle.
Usage of all commands shown is as usual, with they key exception that you'll be
providing them with a secret key for the anonymization.

Double-blind ``reviews assign``
-------------------------------

I order to run ``reviews assign`` in double-blind mode, all you need to do in
addition to the no-blind usage is to supply the ``--double-blind-key`` argument.

.. code-block:: bash
    :caption: Assigning double-blind reviews

    $ repobee reviews assign -a task-1 --sf students.txt --double-blind-key SUPER_SECRET_KEY

The key is a secret, do not share it with the students. After assigning reviews
with a given key, you must also remember or otherwise store that key until those
reviews are closed, or you will be unable to interact with the anonymous repos.

.. important::

    The double-blind key is a **secret**. Given the key, all repositories can be
    deanonymized.

.. important::

    For each review, you must **remember** or **store** the key until reviews
    are closed. Otherwise, you can't deanonymize the repos, and consequently
    can't collect and distribute reviews.

.. important::

    If you run double-blind ``reviews assign`` for with ``--num-reviews``
    larger than ``1``, reviewers reviewing the same repository will be able to
    see each others' reviews.

Double-blind ``reviews check``
------------------------------

Just like with ``reviews assign``, the only thing you need to add in addition to
normal usage is the ``--double-blind-key`` argument.

.. code-block:: bash
    :caption: Checking the status of double-blind reviews

    $ repobee reviews check \
        --assignments task-1 \
        --sf students.txt \
        --num-reviews 1 \
        --title-regex '\APeer review\Z' \
        --double-blind-key SUPER_SECRET_KEY

The repositories are deanonymized, and the output looks precisely like that of
no-blind review. Needless to say, your students should not be shown this
output.

``SUPER_SECRET_KEY`` must match the key you supplied to ``reviews assign``.

Collecting double-blind reviews with ``issues list``
----------------------------------------------------

Once you've verified that the students have performed their reviews with
``reviews check``, you can collect reviews with ``issues list``. Here, you need
to specify two arguments out of the ordinary: ``--double-blind-key`` with your
secret key, as well as ``--hook-results-file`` to store the issues locally.
To collect only the reviews, with title "Peer review", the command could look
like so.

.. code-block:: bash
    :caption: Collecting double-blind review issues

    $ repobee issues list \
        --assignments task-1 \
        --sf students.txt \
        --title-regex '\APeer review\Z' \
        --hook-results-file results.json \
        --double-blind-key SUPER_SECRET_KEY

By specifying the title regex your students use for review, you don't collect
the instructions. If you'd like to also collect and distribute the instructions
to the original repos, you can either use a carefully crafted regex for it, or
simply provide the empty strigle (i.e. ``--title-regex ""``), which will match
any issue.

Note that you can now also browse the reviews before distribution by viewing
the ``results.json`` file.

Distributing double-blind reviews with ``issues open``
------------------------------------------------------

In order for students to actually be able to read the reviews by their peers,
the issues need to be distributed to the original repos. To do this, execute
``issues open`` as per usual, but supply ``--hook-results-file`` instead of
``--issue``.

.. code-block:: bash
    :caption: Distributing double-blind reviews from a hook results file

    $ repobee issues open \
        --assignments task-1 \
        --sf students.txt \
        --hook-results-file results.json

Note that you do not need the key here: the issues in the hook results file are
already deanonymized.

Double-blind ``reviews end``
----------------------------

.. important::

    If using GitHub, your access token must have the ``delete_repo`` scope in
    order to run this command.

``reviews end`` is a cleanup command. When doing no-blind peer review, it's
often necessary to run it as students otherwise maintain read access to
their peers' repositories, and may then be able to view feedback from teachers
or TAs. With double-blind reviews, this isn't the case as the reviewers only
get access to copies of the reviewed repositories. However, it does leave quite
a mess of repositories and review teams with strange names, so cleaning up may
be desirable. If you want to do that, simply run ``reviews end`` and supply
your key.

.. code-block:: bash
    :caption: Ending double-blind reviews

    $ repobee reviews end \
        --assignments task-1 \
        --sf students.txt \
        --double-blind-key SUPER_SECRET_KEY

.. danger::

    Running ``reviews end`` irrevocably destroys all traces of the reviews,
    including deleting the anonymous repositories and review teams. Make sure
    to collect reviews with ``issues list`` before doing this.

And that's pretty much all there is to double-blind review with RepoBee!
