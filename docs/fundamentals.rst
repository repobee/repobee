.. _fundamentals:

Introduction
************
Repomate is an opinionated tool for managing anything from a handful to
thousands of GitHub repositories for higher education courses. It was created as
the old teachers_pet_ tool was getting long in the tooth, and the new `GitHub
Classroom`_ wasn't quite what we wanted (we like our command line apps).
Repomate is heavily inspired by teachers_pet, but tries to both make for a more
complete and streamlined experience.

Philosophy and goals
====================
The primary goal of Repomate is to lower the bar for incorporating
git and GitHub into higher education coursework, hopefully opening up
the wonderful world of version control to teachers who may not be subject
experts (and to their students). For new users, Repomate provides both a
tool and an opinionated workflow to adopt. For the more experienced user,
there is also opportunity to customize Repomate using its plugin system,
which I am looking to expand even more. Repomate is primarily geared toward
course administrators looking to generate repos for their students. Many
features are however highly useful to teaching assistants, such as the ability
to clone repos in bulk and perform arbitrary tasks on them (tasks can be
implemented as plugins, see :ref:`plugins`).

Key concepts
============
Some terms occur frequently in Repomate and are best defined up front.
Some of the descriptions may not click entirely before reading the
:ref:`userguide` section, so quickly browsing through these definitions and
re-visiting them when needed is probably the best course of action.

* *Target organization*: The GitHub Organization_ related to the current course
  round.
* *Master repository*: Or *master repo*, is a template repository upon which
  student repositories are based.
* *Master organization*: The master organization is an optional organization to
  keep master repos in. The idea is to be able to have the master repos in this
  organization to avoid having to migrate them to the target organization for
  each course round. It is highly recommended to use a master organization if
  master repos are being worked on across course rounds.
* *Student repository*: Or *student repo*, refers to a *copy* of a master repo
  for some specific student.
* *GitHub instance*: A hosted GitHub service. This can be for example
  *https://github.com* or any Enterprise host.

.. _conventions:

Conventions
===========
The following conventions are fundamental to working with Repomate.

* For each course and course round, use one target Organization_.
* Any user of Repomate has unrestricted access to the target organization
  (i.e. is an owner).
* Master repos should be available as private repos in one of three places:
  - The master organization (recommended if the master repos are being
  maintained and improved across course rounds).
  - The target organization. If you are doing a trial run or have trivial
  (empty) master repos, this may be a good option.
  - Locally in the current working directory.
* Student repositories are copies of the default branches of the master
  repositories (i.e. ``--single-branch`` cloning is used by default). That is,
  until students make modifications.
* Student repositories are named *<username>-<master_repo_name>* to guarantee
  unique repo names.
* Each student is assigned to a team with the same name as the student's
  username. It is the team that is granted access to the repositories, not
  the student's actual user.
* Student teams have push access to the repositories, but not
  administrative access (i.e. students can't delete their own repos).

.. note::

    Few of these conventions are actually enforced, and there are ways around
    almost every single one. However, with the exception of the *one
    organization per course round* convention, which must be ensured manually,
    Repomate will automatically adhere to the other conventions. Although
    Repomate does adhere to the conventions, there is no way to stop users
    from breaking them using e.g. the GitHub web interface, manually performing
    master repo migrations etc. Straying form the conventions may cause
    Repomate to behave unexpectedly.

.. _teachers_pet: https://github.com/education/teachers_pet
.. _GitHub Classroom: https://classroom.github.com/
.. _Organization: https://help.github.com/articles/about-organizations/
