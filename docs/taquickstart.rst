.. _ta_quickstart:

Teaching Assistant Quickstart
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

To correct student assignments, you will typically want to clone them to your
local machine. The basics of this is described in :ref:`clone_action`. You also
have possibilities to customize your workflow by using or creating plugins.
Some of the :ref:`builtins` may be useful to you, such as the :ref:`auto_javac`
plugin that tries to compile the students' Java code, or the :ref:`auto_pylint`
plugin that runs ``pylint`` on Python code. See :ref:`plugins` for details on
how to use plugins.

See the :ref:`cli` for further details on the exact options you can use when
cloning with ``repos clone``. For example, the ``--update-local`` option is
very useful for being able to update previously cloned repositories.

Providing feedback on the issue tracker
=======================================

For courses that provide student feedback by opening issues, the `feedback
plugin <https://github.com/repobee/repobee-feedback>`_ is very useful. It
allows you to write your feedback locally, and then open issues for all of your
students at the same time. This also means that you don't have to do all of
your correcting in one go, but can do it incrementally, and still be able to
easily provide feedback to all students at the same time. You can install it
with ``repobee plugin install`` and then activate it with ``repobee plugin
activate``. This adds the ``issues feedback`` command, that allows you to open
feedback issues in bulk. See the `feedback plugin
<https://github.com/repobee/repobee-feedback>`_ docs for details on usage.

In conjunction with opening issues on the issue tracker, it's useful to be able
to have a look at what issues you've opened. The ``issues list`` command allows
you to do just that. See the :ref:`issues_list` part of the user guide for more
details on that.

Finally, you may want to clean up your issue tracker by closing issues. The
``issues close`` command allows you to do that, and you can find details on
using it in the :ref:`close` part of the user guide.
