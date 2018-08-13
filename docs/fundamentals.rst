.. _fundamentals:

Fundamentals
************
``gits_pet`` is an opinionated tool for managing large amounts of ``GitHub``
repositories for higher education courses. It was created as a result of the
old teachers_pet_ tool not quite meeting our desires, and ``GitHub``'s migration
over to the browser based `GitHub Classroom`_.

Philosophy and Goals
====================
The primary mission of ``gits_pet`` is to lower the entry level for
incorporating ``git`` and ``GitHub`` into courses, hopefully opening up the
wonderful world of version control to teachers who may not be experts in the
area. As such, ``gits_pet`` is firmly seated in the convention over
configuration camp, favoring highly opinionated workflows that are easy to get
started with rather than highly configurable ones. The target audience is
primarily teachers seeking to incorporate ``git`` and ``GitHub`` into their
courses, but lack the time or the expertise to do it from scratch.

Terminology
===========
Some terms occur frequently in ``gits_pet`` and are best defined up front.
Some of the descriptions may not click entirely before reading the Workflow_
section, so quickly browsing through these definitions and re-visiting them
when needed is probably the best course of action.

* *Target organization*: The GitHub Organization_ related to the current course
  round.
* *Master repository*: Or *master repo*, is a template repository upon which
  student repositories are based.
* *Student repository*: Or *student repo*, refers to a *copy* of a master repo
  for some specific student.
* *GitHub instance*: A hosted GitHub service. This can be for example
  ``https://github.com`` or any Enterprise host.

.. _Workflow:

Getting Started
===============
The basic workflow of ``gits_pet`` is best described by example. In this section,
I will walk you through how to set up an Organization_ with master and student
repositories by showing every single step I would perform myself.

Create an Organization_
-----------------------
   
This is an absolutely necessary pre-requisite for using ``gits_pet``.
Create an organization with an appropriate name on the GitHub instance you
intend to use. I will call my *target organization* ``gits_pet_demo``, so
whenever you see that, substitute in the name of your target organization.

Configure ``gits_pet`` for the target organization
--------------------------------------------------

First of all, see the :ref:`configuration` section for how to acquire an OAUTH
token and where to put the configuration file. Setting the token is easy in
``bash``. Just add the following line to your ``bash`` config file
(``~/.bashrc`` on most Linux distros, and ``~/.bash_profile`` on OSX).

.. code-block:: bash
    
    export GITS_PET_OAUTH=<SUPER SECRET TOKEN>

When that's added, either source the file with ``source path/to/bash/config``
or simply start another ``bash`` shell, which will automatically read the
file. Verify that the token is there by typing:

.. code-block:: bash

    $ echo $GITS_PET_OAUTH

You should see your token in the output. With that out of the way, let's create
a configuration file. We can use ``gits_pet`` to figure out where it should
be located.

.. code-block:: bash
    
    $ gits_pet -h
    [INFO] no config file found. Expected config file location: /home/USERNAME/.config/gits_pet/config.cnf

    <HELP MESSAGE OMITTED>

At the very top, you will find the expected config file location. The exact
path will vary depending on operating system and username.






Workflow
========
The basic workflow of ``gits_pet`` looks something like this:

1. Create a GitHub Organization_. We recommend using one Organization_ per
   course and course round, referred to as the *target organization*.

   - We also recommend creating a configuration file at this point, see the
     :ref:`configuration` section for details.

   - All usage examples from now on will assume that the ``github_base_url``,
     ``user`` and ``org_name`` parameters have been configured in the
     configuration file.

2. Use the ``migrate`` command to move master repositories into the target
   organization.
   
    - The master repositories can either be local and specified by file path,
      or remote and specified by url.  These repositories will automatically be
      added to the ``master_repos`` team for easy access.

    - Example (repos in current directory): ``gits_pet migrate -mn
      master-repo-1 master-repo-2`` - For remote repos, specify ``-mu
      [REPO_URLS ...]`` instead.

    - While this is not *strictly* required at this point, as local repos can
      also be used as master repos, it is **highly** recommended. It's also
      really easy, so why not?

3. Setup the student repos with the ``setup`` command. This command creates one
   team per student and adds the students to their teams. Then, for each master
   repo, it creates an identical copy (of the ``master`` branch only!) for each
   student.


    - Example (assuming a students file called ``students``): ``gits_pet setup -mn master-repo-1 master-repo-2 --sf students``



.. _teachers_pet: https://github.com/education/teachers_pet
.. _GitHub Classroom: https://classroom.github.com/
.. _Organization: https://help.github.com/articles/about-organizations/
