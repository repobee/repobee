.. _ta_quickstart:

Teaching assistant quickstart
*****************************

The full RepoBee user guide is heavily centered on the repo administration
aspects of RepoBee, which is typically the responsibility of the course
responsible. As a teaching assistant using RepoBee, most of that is probably
noise to you. This guide is intended to give teaching assistants using RepoBee a
quickstart in its use, without having to sift through the entire user guide.

Install and configure RepoBee
=============================

Of course, you will need to both install and configure RepoBee before you can
use it. See :ref:`install` for install instructions, and :ref:`config` for how
to configure it. As a teaching assistant, you typically don't need to configure
the ``template_org_name``, but it is very convenient to configure the students
file for the students or groups that you are responsible for.

Cloning repositories
====================

Something that you will typically do frequently is to clone repositories. The
basics of this is described in :ref:`clone_action`. You also have possibilities
to customize your workflow by using or creating plugins. Some of the
:ref:`builtins` may be useful to you, such as the :ref:`auto_javac` plugin that
tries to compile the students' Java code, or the :ref:`auto_pylint` plugin that
runs ``pylint`` on Python code.
