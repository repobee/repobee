.. _fundamentals:

Introduction
************
RepoBee is a command line tool for enabling teachers and teaching assistants to
manage anything from a handful to thousands of Git repositories for students on
the GitHub, GitLab and Gitea platforms. It has two key features that separates
it from contemporary solutions: support for multiple hosting platforms, and a
plugin system for extending and customizing its behavior. Our vision for
RepoBee is to make it simple to pick up for the novice user, yet extensible and
customizable for the more seasoned user.

Key concepts
============
Some terms occur frequently in RepoBee and are best defined up front.
Some of the descriptions may not click entirely before reading the
:ref:`userguide` section, so quickly browsing through these definitions and
re-visiting them when needed is probably the best course of action. As GitHub is
the default platform, these concepts are based on and often refer to
GitHub-specific terms. For a mapping to GitLab terms and concepts, please see
the :ref:`gitlab` section.

* *Platform*: Or *hosting platform*, refers a service such as Github.
* *Platform instance:* A specific instance of a hosting platform. For example,
  https://github.com is one instance, and an arbitrary GitLab Enterprise
  installation is another.
* *Target organization*: The organization (or with GitLab, group) related to
  the current course round.
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

* Template repos should be available as private or public repos in one of three places:

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
should be aware of. RepoBee also supports GitLab through the ``gitlab`` plugin,
and Gitea through the ``gitea`` plugin.

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
* **Gitea:** All Gitea organizations support private repositories.

Students are added to the target Organization slightly differently
------------------------------------------------------------------
During setup, students are added to their respective Teams. Precisely how this
happens differs slightly.

* **Enterprise:** Students are automatically added to their Teams in the Organization.
* **github.com:** Students are invited to the Organization and added to their Teams upon accepting.
* **GitLab:** Students are automatically added, both on self-hosted and https://gitlab.com.
* **Gitea:** Students are automatically added.
