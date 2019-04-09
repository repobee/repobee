.. _fundamentals:

Introduction
************
RepoBee is an opinionated tool for managing anything from a handful to
thousands of GitHub repositories for higher education courses. It was created as
the old teachers_pet_ tool was getting long in the tooth, and the new `GitHub
Classroom`_ wasn't quite what we wanted (we like our command line apps).
RepoBee is heavily inspired by teachers_pet, but tries to both make for a more
complete and streamlined experience.

Philosophy and goals
====================
The primary goal of RepoBee is to lower the bar for incorporating
Git and GitHub into higher education coursework, hopefully opening up
the wonderful world of version control to teachers who may not be subject
experts (and to their students). For new users, RepoBee provides both a
tool and an opinionated workflow to adopt. For the more experienced user,
there is also opportunity to customize RepoBee using its plugin system,
which is planned to be expanded even more. RepoBee is primarily geared toward
teachers looking to generate repos for their students. Many features are
however highly useful to teaching assistants, such as the ability to clone
repos in bulk and perform arbitrary tasks on them (tasks can be implemented as
plugins, see :ref:`plugins`).

Another key goal is to keep RepoBee simple to use and simple to maintain.
RepoBee requires a minimal amount of static data to operate (such as a list of
students, a URL to the GitHub instance and an access token to GitHub), which
can all be provided in configuration files or on the command line, but it does
not require any kind of backing database to keep track of repositories. That is
because RepoBee itself does not keep track of anything, except possibly for the
aforementioned static data if one chooses to keep it in configuration files.
All of the complex state state is more or less implicitly stored on GitHub, and
RepoBee locates student repositories based on strict naming conventions that
are enforced by all of its commands. This allows RepoBee to be simple to set up
and use on multiple machines, which is crucial in a course where multiple
teachers and TAs are managing the student repositories. There is also the fact
that nothing need be installed server-side, as RepoBee only uses core GitHub
features to do its work. For an experienced user, installing RepoBee and
setting everything up for a new course can literally take minutes. For the
novice, the :ref:`userguide` will hopefully prove sufficient to get started in
not too much time.

Key concepts
============
Some terms occur frequently in RepoBee and are best defined up front.
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
  for some specific student or group of students.
* *GitHub instance*: A hosted GitHub service. This can be for example
  *https://github.com* or any Enterprise host.

.. _conventions:

Conventions
===========
The following conventions are fundamental to working with RepoBee.

* For each course and course round, use one target Organization_.
* Any user of RepoBee has unrestricted access to the target organization
  (i.e. is an owner). If the user has limited access, some features may work,
  while others may not.
* Master repos should be available as private repos in one of three places:
  - The master organization (recommended if the master repos are being
  maintained and improved across course rounds).
  - The target organization. If you are doing a trial run or for some reason
  can't have multiple organizations, this may be a good option.
  - Locally in the current working directory. If your master repos are trivial
  (e.g. empty), this may be a good option.
* Student repositories are copies of the default branches of the master
  repositories (i.e. ``--single-branch`` cloning is used by default). That is,
  until students make modifications.
* Student repositories are named *<username>-<master_repo_name>* to guarantee
  unique repo names.
  - Student repositories belonging to groups of students are named
  *<username-1>-<username-2>-...-<master-repo-name>*.
* Each student is assigned to a team with the same name as the student's
  username (or a concatenation of usernames for groups). It is the team that is
  granted access to the repositories, not the student's actual user.
* Student teams have push access to the repositories, but not
  administrative access (i.e. students can't delete their own repos).

.. note::

    Few of these conventions are actually enforced, and there are ways around
    almost every single one. However, with the exception of the *one
    organization per course round* convention, which must be ensured manually,
    RepoBee will automatically adhere to the other conventions. Although
    RepoBee does adhere to the conventions, there is no way to stop users
    from breaking them using e.g. the GitHub web interface, manually performing
    master repo migrations etc. Straying form the conventions may cause
    RepoBee to behave unexpectedly.

.. _teachers_pet: https://github.com/education/teachers_pet
.. _GitHub Classroom: https://classroom.github.com/
.. _Organization: https://help.github.com/articles/about-organizations/
