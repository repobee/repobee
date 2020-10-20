.. _fundamentals:

Introduction
************
RepoBee is an opinionated tool for managing anything from a handful to
thousands of Git repositories on the GitHub and GitLab platforms. There were two
primary reasons for RepoBee's inception. First, the old teachers_pet_ tool that
we used previously lacked some functionality that we needed and had been
archived in favor of the new `GitHub Classroom`_. Second, `GitHub Classroom`_
did not support GitHub Enterprise at the time, was not customizable enough, and
also gone closed source, which runs contrary to our values and goals.

RepoBee is our answer to these needs. It is heavily inspired by teachers_pet_,
as we enjoyed the overall workflow, but improves on the user experience in
every conceivable way.

Philosophy and goals
====================
When RepoBee was first created, it's goals were simple: facilitate creation and
management of student repositories for courses at KTH, using GitHub Enterprise.
Since then, the scope of the project has grown to incorporate many new features,
including support for the GitLab platform. For new users of Git+GitHub/GitLab in
education, RepoBee provides both a tool to make it happen, and an opinionated
workflow to ease the transition. For the more experienced user, the plugin system
can be used to extend or modify the behavior of RepoBee. While creating a plugin
requires some rudimentary skills with Python programming, installing a plugin is
effortless. The plugin system enables RepoBee to both be easy to get up and
running *without* any required customization, while still *allowing* for a
degree of customization to those that want it. See :ref:`plugins` for details.

Another key goal is to keep RepoBee simple to use and simple to maintain.
RepoBee requires a minimal amount of static data to operate (such as a list of
students, a URL to the platform instance and an access token to said platform),
which can all be provided in configuration files or on the command line. It
does not require any kind of backing database to keep track of repositories.
In fact, RepoBee itself keeps track of little more than its own version, and
which plugins are currently installed and active. All of the complex state
state is more or less implicitly stored on the hosting platform. This allows
RepoBee to be simple to set up and use on multiple machines, which is crucial
in a course where multiple teachers and TAs are managing the student
repositories.

RepoBee is very intentionally designed *not* to be a service, but an on-demand
tool that is only in use when explicitly being used. This means that nothing
needs to be installed server-side for RepoBee to function, which also happens
to be key to supporting multiple hosting platforms. For an experienced user,
installing RepoBee and setting everything up for a new course can literally
take minutes  For the novice, the :ref:`userguide` will hopefully prove
sufficient to get started within the hour.

Key concepts
============
Some terms occur frequently in RepoBee and are best defined up front.
Some of the descriptions may not click entirely before reading the
:ref:`userguide` section, so quickly browsing through these definitions and
re-visiting them when needed is probably the best course of action. As GitHub is
the default platform, these concepts are based on and often refer to
GitHub-specific terms. For a mapping to GitLab terms and concepts, please see
the :ref:`gitlab` section.

* *Platform*: Or *hosting platform*, refers to services such as GitHub and
  GitLab.
* *Platform instance:* A specific instance of a hosting platform. For example,
  https://github.com is one instance, and an arbitrary GitLab Enterprise
  installation is another.
* *Target organization*: The GitHub Organization_ related to the current course
  round.
* *Assignment*: What you would expect; an assignment to be handed in.
* *Template repository*: Or *template repo*, is a template from which student
  repositories are created for a given assignment. Each assignment has one
  associated template repo. Template repos share the name of their associated
  assignment.
* *Template organization*: The template organization is an optional
  organization to keep template repos in. The idea is to be able to have the
  template repos in this organization to avoid having to migrate them to the
  target organization for each course round. It is highly recommended to use a
  template organization if template repos are being worked on across course
  rounds.
* *Student repository*: Or *student repo*, refers to a *copy* of a template
  repo for some specific student or group of students.

.. _conventions:

Conventions
===========
The following conventions are fundamental to working with RepoBee.

* For each course and course round, use one target organization.
* Any user of RepoBee has unrestricted access to the target organization
  (i.e. is an owner). If the user has limited access, some features may work,
  while others may not.

  - The :ref:`auto_tamanager` plugin provides functionality for assigning
    teaching assistants to the organization with significantly fewer
    privileges than an owner. These users cannot use the full power of RepoBee,
    but it is sufficient for e.g. cloning repositories and opening issues on
    the issue trackers.

* Template repos should be available as private repos in one of three places:

  - The template organization (recommended if the template repos are being
    maintained and improved across course rounds).
  - The target organization. If you are doing a trial run or for some reason
    can't have multiple organizations, this may be a good option.
  - Locally in the current working directory. If your template repos are trivial
    (e.g. empty), this may be a good option.
* Student repositories are copies of the default branches of the template
  repositories (i.e. ``--single-branch`` cloning is used by default). That is,
  until students make modifications.

  - An implication of this is that you can have solutions to the assignments on
    a different branch in the template repository. See `repobee-sanitizer
    <https://github.com/repobee/repobee-sanitizer>`_ for a plugin that we use
    to maintain a separate branch with solutions.
* Student repositories are named *<username>-<assignment-name>* to guarantee
  unique repo names.
  - Student repositories belonging to groups of students are named
  *<username-1>-<username-2>-...-<assignment-name>*.
* Each student is assigned to a team with the same name as the student's
  username (or a concatenation of usernames for groups). It is the team that is
  granted access to the repositories, not the student's actual user.
* Student teams have push access to the repositories.

.. note::

   RepoBee has no way of enforcing these conventions, other than itself strictly
   adhering to them. For example, there are no countermeasures against someone
   manually changing the names of student repositories or their URLs, and as
   there are endless variations of things that can be manually changed, there
   are no safety checks against such things either. If you have a need to
   manually change something, do keep in mind that straying from RepoBee's
   conventions may cause it to act unexpectedly.

Usage with different platforms (GitHub, GitHub Enterprise and GitLab)
=====================================================================
RepoBee was originally designed for use with GitHub Enterprise, but also works
well with the public cloud service at https://github.com. Usage of RepoBee
should be identical, but there are two differences between the two that one
should be aware of. RepoBee also supports GitLab through the ``gitlab`` plugin.

In the following sections, we outline the platform-dependent variations in
usage that we are aware of.


The Organization must have support for private repositories
-----------------------------------------------------------
Private repositories are key to keep students from being able to see each
others' work, and thereby avoid a few avenues for plagiarism.

* **Enterprise:** All Organizations on Enterprise support private repositories.
* **github.com:** You need a paid Organization (confusingly called a *Team*,
  but unrelated to the Teams *inside* an Organization). Educators and
  researchers can get such Organization accounts for free,
  see `how to get the discount here
  <https://help.github.com/en/articles/applying-for-an-educator-or-researcher-discount>`_.
* **GitLab:** All GitLab groups (self-hosted and on https://gitlab.com) support
  private repositories.

Students are added to the target Organization slightly differently
------------------------------------------------------------------
During setup, students are added to their respective Teams. Precisely how this
happens differs slightly.

* **Enterprise:** Students are automatically added to their Teams in the Organization.
* **github.com:** Students are invited to the Organization and added to their Teams upon accepting.
* **GitLab:** Students are automatically added, both on self-hosted and https://gitlab.com.

.. _teachers_pet: https://github.com/education/teachers_pet
.. _GitHub Classroom: https://classroom.github.com/
.. _Organization: https://help.github.com/articles/about-organizations/
.. _faculty: https://help.github.com/en/articles/applying-for-an-educator-or-researcher-discount
