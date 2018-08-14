.. _fundamentals:

Fundamentals
************
``gits_pet`` is an opinionated tool for managing large amounts of ``GitHub``
repositories for higher education courses. It was created as a result of the
old teachers_pet_ tool not fulfilling our every desire, as well as ``GitHub``'s
migration over to the browser based `GitHub Classroom`_, which did not quite
strike our fancy. ``gits_pet`` is essentially a newer (and hopefully better)
version of ``teachers_pet``, written in Python (which is commonly used at KTH)
instead of Ruby (which is barely used at all).

Philosophy and Goals
====================
The primary goal of ``gits_pet`` is to lower the entry level for incorporating
``git`` and ``GitHub`` into higher education coursework, hopefully opening up
the wonderful world of version control to teachers who may not be subject
experts (and to their students). As such, ``gits_pet`` is firmly seated in the
convention over configuration camp, favoring highly opinionated workflows that
are easy to get started with, rather than highly configurable ones. The target
audience is primarily teachers seeking to incorporate ``git`` and ``GitHub``
into their courses, but lack the time or expertise to build their own
automation system from scratch.

.. note::

    Is there a difference between ``git`` and ``GitHub``? Yes! ``git`` is the
    version control system, and ``GitHub`` is a company that hosts ``git``
    servers on ``github.com``, and provides enterprise software for hosting
    your ``GitHub`` instances.

Terminology
===========
Some terms occur frequently in ``gits_pet`` and are best defined up front.
Some of the descriptions may not click entirely before reading the
:ref:`Getting-Started` section, so quickly browsing through these definitions and
re-visiting them when needed is probably the best course of action.

* *Target organization*: The GitHub Organization_ related to the current course
  round.
* *Master repository*: Or *master repo*, is a template repository upon which
  student repositories are based.
* *Student repository*: Or *student repo*, refers to a *copy* of a master repo
  for some specific student.
* *GitHub instance*: A hosted GitHub service. This can be for example
  ``https://github.com`` or any Enterprise host.

Conventions
===========
The following conventions are fundamental to working with ``gits_pet``.

* For each course and course round, use one Organization_.
* Master repositories should be available as private repositories in the
  Organization_ (using local repos on the current machine is also *ok* and
  generally works well).
* Master repositories are added to the ``master_repos`` team.
* Student repositories are copies of the default branches of the master
  repositories (i.e. ``--single-branch`` cloning is used by default).
* Student repositories are named ``<username>-<master_repo_name>`` to guarantee
  unique repo names.
* Each student is assigned to a team with the same name as the student's
  username. It is the team that is granted access to the repositories, not
  the student's actual user.
* Student teams have ``push`` access to the repositories, but not
  administrative access (i.e. students can't delete their own repos).

.. note::

    Few of these conventions are actually enforced, and there are ways around
    almost every single one. However, with the exception of the *one
    organization per course round* convention, which must be ensured manually,
    ``gits_pet`` will automatically adhere to the other conventions. Although
    ``gits_pet`` does adhere to the conventions, there is no way to stop users
    from breaking them using e.g. the GitHub web interface, manually performing
    master repo migrations etc. Straying form the conventions may cause
    ``gits_pet`` to behave unexpectedly.

.. _teachers_pet: https://github.com/education/teachers_pet
.. _GitHub Classroom: https://classroom.github.com/
.. _Organization: https://help.github.com/articles/about-organizations/
