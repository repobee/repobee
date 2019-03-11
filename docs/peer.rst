.. _peer review:

Peer review (``assign-reviews`` and ``purge-review-teams`` commands)
**********************************************************************************************
Peer reviewing is an important part of a programming curriculum, so of course
``repomate`` facilitates this! The relevant commands are
``assign-reviews`` and ``purge-review-teams``.
Like much of the other functionality in ``repomate``, the peer review
functionality is built around teams and limited access privileges. In short,
every student repo up for review gets an associated peer review team generated,
which has ``pull`` access to the repo. Each student then gets added to ``0 < N
< num_students`` peer review teams, and are to open a peer review issue in the
associated repos. This is at least the the default. See :ref:`review allocation
algorithm` for other available review allocation schemes.

.. important::

   The commands ``assign-peer-reviews``,
   ``purge-peer-review-teams`` and ``check-peer-review-progress`` have been
   renamed ``assign-reviews``, ``purge-review-teams`` and ``check-reviews``,
   respectively. The functionality is unchanged, and the old commands will
   continue to work until ``v2.0.0`` is released. At that point, the old
   commands will be removed.

.. _assign reviews:

Getting started with peer reviews using ``assign-reviews``
=================================================================
The bulk of the work is performed by ``assign-reviews``. Let's have a
look at the help message (i.e. run ``repomate assign-reviews -h``):

.. code-block:: bash

    $ repomate assign-reviews -h
    usage: repomate assign-reviews [-h]
                                   (-sf STUDENTS_FILE | -s STUDENTS [STUDENTS ...])
                                   [-o ORG_NAME] [-g GITHUB_BASE_URL] [-t TOKEN]
                                   [-tb] -mn MASTER_REPO_NAMES
                                   [MASTER_REPO_NAMES ...] [-n N] [-i ISSUE]

    For each student repo, create a review team with pull access named
    <student>-<master_repo_name>-review and randomly assign other students to it.
    All students are assigned to the same amount of review teams, as specified by
    `--num-reviews`. Note that `--num-reviews` must be strictly less than the
    amount of students.

    optional arguments:
      -h, --help            show this help message and exit
      -sf STUDENTS_FILE, --students-file STUDENTS_FILE
                            Path to a list of student usernames.
      -s STUDENTS [STUDENTS ...], --students STUDENTS [STUDENTS ...]
                            One or more whitespace separated student usernames.
      -o ORG_NAME, --org-name ORG_NAME
                            Name of the target organization
      -g GITHUB_BASE_URL, --github-base-url GITHUB_BASE_URL
                            Base url to a GitHub v3 API. For enterprise, this is
                            usually `https://<HOST>/api/v3`
      -t TOKEN, --token TOKEN
                            OAUTH token for the GitHub instance. Can also be
                            specified in the `REPOMATE_OAUTH` environment
                            variable.
      -tb, --traceback      Show the full traceback of critical exceptions.
      -mn MASTER_REPO_NAMES [MASTER_REPO_NAMES ...], --master-repo-names MASTER_REPO_NAMES [MASTER_REPO_NAMES ...]
                            One or more names of master repositories. Names must
                            either refer to local directories, or to master
                            repositories in the target organization.
      -n N, --num-reviews N
                            Assign each student to review n repos (consequently,
                            each repo is reviewed by n students). n must be
                            strictly smaller than the amount of students.
      -i ISSUE, --issue ISSUE
                            Path to an issue to open in student repos. If
                            specified, this issue will be opened in each student
                            repo, and the body will be prepended with user
                            mentions of all students assigned to review the repo.
                            NOTE: The first line is assumed to be the title.

Most of this, we've seen before. The only non-standard arguments are
``--issue`` and ``--num-reviews``, the former of which we've actually already
seen in the ``open-issues`` command (see :ref:`open`). I will assume that both
``--github-base-url`` and ``--org-name`` are already configured in the
configuration file (if you don't know what this mean, have a look at
:ref:`config`). Thus, the only things we must specify are
``--students/--students-file`` and ``--num-reviews`` (``--issue`` is optional,
more on that later). Let's make a minimal call with the
``assign-reviews`` command, and then inspect the log output to figure
out what happened. Recall that ``students.txt`` lists our three favorite
students spam, ham and eggs (see :ref:`setup`).

.. code-block:: bash

    $ repomate assign-reviews -mn master-repo-1 -sf students.txt --num-reviews 2
    # step 1
    [INFO] created team spam-master-repo-1-review
    [INFO] created team eggs-master-repo-1-review
    [INFO] created team ham-master-repo-1-review
    # step 2
    [INFO] adding members eggs, ham to team spam-master-repo-1-review
    [INFO] adding members ham, spam to team eggs-master-repo-1-review
    [INFO] adding members spam, eggs to team ham-master-repo-1-review
    # steps 3 and 4, interleaved
    [INFO] opened issue eggs-master-repo-1/#1-'Peer review'
    [INFO] adding team eggs-master-repo-1-review to repo eggs-master-repo-1 with 'pull' permission
    [INFO] opened issue ham-master-repo-1/#2-'Peer review'
    [INFO] adding team ham-master-repo-1-review to repo ham-master-repo-1 with 'pull' permission
    [INFO] opened issue spam-master-repo-1/#2-'Peer review'
    [INFO] adding team spam-master-repo-1-review to repo spam-master-repo-1 with 'pull' permission

The following steps were performed:

1. One review team per repo was created (``<student>-master-repo-1-review``).
2. Two students were added to each review team. Note that these allocations are
   _random_. For obvious resons, there can be at most ``num_students-1`` peer
   reviews per repo. So, in this case, we are at the maximum.
3. An issue was opened in each repo with the title ``Peer review``, and a body
   saying something like ``You should peer review this repo.``. The review team
   students were assigned to the issue as well (although this is not apparent
   from the logging).
4. The review teams were added to their corresponding repoos with ``pull``
   permission. This permission allows members of the team to view the repo and
   open issues, but they can't push to (and therefore can't modify) the repo.

That's it for the basic functionality. The intent is that students should open
an issue in every repo they are to peer review, with a specific title. The title
can then be regexed in the upcoming ``check-review-progress`` to see which
students assigned to the different peer review teams have created their review
issue. Of course, other schemes can be cooked up, but that is my current vision
of how I myself will use it. Now, let's talk a bit about that ``--issue``
argument.

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
``master-repo-2`` repo, and the students should review tasks 2 and 3 based on
some criteria. It would then be beneficial to specify this in the peer review
issue, so we'll write up our own little issue to replace the default one.
Remember that the first line is taken to be the title, in exactly the same way
as issue files are treated in :ref:`open`.

.. code-block:: none

    Review of master-repo-2

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

    $ repomate assign-reviews -mn master-repo-2 -sf students.txt --num-reviews 2 --issue issue.md
    [INFO] created team spam-master-repo-2-review
    [INFO] created team eggs-master-repo-2-review
    [INFO] created team ham-master-repo-2-review
    [INFO] adding members ham, eggs to team spam-master-repo-2-review
    [INFO] adding members spam, ham to team eggs-master-repo-2-review
    [INFO] adding members eggs, spam to team ham-master-repo-2-review
    [INFO] opened issue eggs-master-repo-2/#2-'Review of master-repo-2'
    [INFO] adding team eggs-master-repo-2-review to repo eggs-master-repo-2 with 'pull' permission
    [INFO] opened issue ham-master-repo-2/#2-'Review of master-repo-2'
    [INFO] adding team ham-master-repo-2-review to repo ham-master-repo-2 with 'pull' permission
    [INFO] opened issue spam-master-repo-2/#2-'Review of master-repo-2'
    [INFO] adding team spam-master-repo-2-review to repo spam-master-repo-2 with 'pull' permission

As you can tell from the last few lines, the title is the one specified in the
issue, and not the default title as it was before. And that's pretty much it for
setting up the peer review repos.


.. _purge peer review teams:

Cleaning with ``purge-review-teams``
=========================================
The one downside of using teams for access privileges is that we bloat the
organization with a ton of teams. Once the deadline has passed and all peer
reviews are done, there is little reason to keep them (in my mind). Therefore,
the ``purge-review-teams`` command can be used to remove all peer review
teams for a given set of student repos. Let's say that we're completely done
with the peer reviews of ``master-repo-1``, and want to remove the review teams.
It's as simple as:

.. code-block:: bash

    $ repomate purge-review-teams -mn master-repo-1 -sf students.txt
    [INFO] deleted team eggs-master-repo-1-review
    [INFO] deleted team ham-master-repo-1-review
    [INFO] deleted team spam-master-repo-1-review

And that's it, the review teams are gone. If you also want to close the related
issues, you can simply use the ``close-issues`` command for that (see
:ref:`close`). ``purge-review-teams`` plays one more important role:
if you mess something up when assigning the peer reviews. The next section
details how you can deal with such a scenario.

Messing up and getting back on track
====================================
Let's say you messed something up with allocating the peer reviews. For example,
if you left out a student, there is no easy way to rectify the allocations such
that that student is included. Let's say we did just that, and forgot to include
the student ``cabbage`` in the reviews for ``master-repo-2`` back at
:ref:`assign reviews`. We then do the following:

1. Check if any reviews have already been posted. This can easily be performed
   with ``repomate list-issues -mn master-repo-2 -sf students.txt -r '^Peer
   review$'`` (assuming the naming conventions were followed!). Take appropriate
   action if you find any reviews already posted (appropriate being anything you
   see fit to alleviate the situation of affected students possibly being
   assigned new repos to review).
2. Purge the review teams with ``repomate purge-review-teams -mn master-repo-2
   -sf students.txt``
3. Close all review issues with ``repomate close-issues -mn master-repo-2 -sf
   students.txt -r '^Review of master-repo-2$'``
4. Create a new ``issue.md`` file apologetically explaining that you messed up:

.. code-block:: none

    Review of master-repo-2 (for real this time!)

    Sorry, I messed up with the allocations previously. Disregard the previous
    allocations (repo access has been revoked anyway).

5. Assign peer reviews again, with the new issue, with repomate
   ``assign-reviews -mn master-repo-2 -sf students.txt --num-reviews 2
   --issue issue.md``

And that's it! Disaster averted.


.. _review allocation algorithm:

Selecting peer review allocation algorithm
==========================================
The default allocation algorithm is as described in :ref:`peer review`, and is
suitable for when reviewers do not need to interact with the students whom they
review. This is however not always the case, sometimes it is beneficial for
reviewers to to interact with reviewees (is that a word?), especially if the
peer review is done in the classroom. Because of this, ``repomate`` also
provides a _pairwise_ allocation scheme, which allocates reviews such that
if student ``A`` reviews student ``B``, then student ``B`` reviews student
``A`` (except for an ``A->B->C->A`` kind of deal in one group if there are an
odd amount of students). This implemented as a plugin, so to run with this
scheme, you add ``-p pairwise`` in front of the command.

.. code-block:: bash

    $ repomate -p pairwise assign-reviews -mn master-repo-1 -sf students.txt

Note that the pairwise algorithm ignores the ``--num-reviews`` argument, and
will issue a warning if this is set (to anything but 1, but you should just not
specify it). For more details on plugins in ``repomate``, :ref:`plugins`.
