.. _gitea_instructions:

RepoBee and Gitea
*****************

.. danger::

    Gitea support in RepoBee is in early development. All features are
    implemented, but there are known shortcomings and we currently don't
    recommend using it in a live environment.

RepoBee supports `Gitea <https://gitea.io/en-us/>`_ through the built-in
``gitea`` plugin. Gitea is very similar to GitHub, and the terminology
relating to RepoBee (organization, team, etc) is identical.

How to use RepoBee with Gitea
=============================

You must use the ``gitea`` plugin for RepoBee to be able to interface with a
Gitea instance. See :ref:`configure_plugs` for instructions on how to use
plugins. This is one of those plugins that you'll want to activate persistently
with ``plugin activate``. Other than that, usage with Gitea is identical to
that with GitHub.

.. _gitea_base_url:

Specifying the base url
-----------------------

As with GitHub, the base url to given to RepoBee must point directly to the
API. Currently, Gitea's API is located at ``https://your.gitea.domain/api/v1``.
See :ref:`trying_gitea` for a complete example configuration.

.. _gitea_access_token:

Getting an access token for Gitea
---------------------------------

To create a personal access token for a Gitea instance, log in and then click
your profile picture in the top right corner. From there, click ``Settings``
and then go to the ``Applications`` menu.  At the top you'll find a small
section for generating a new token.

.. _gitea_organization:

Creating an organization
------------------------

In order to use RepoBee, you must at least have a target organization to store
student repositories in. To create an organization on Gitea, click the ``+``
drop-down in the top right corner, and then click ``New Organization``.

.. _trying_gitea:

Trying out RepoBee with the Gitea test instance
===============================================

We provide a test instance at https://gitea.repobee.org on which you can play
around with RepoBee in an environment where messing up isn't a big deal. To use
the test instance, simply sign up (you can use a bogus email address) and have
fun!

.. important::

    The test instance is automatically wiped clean every 24 hours at around
    1-2am UTC. No data is retained, be that accounts or repository contents, so
    don't store anything important on the instance!

Signing up and setting up
-------------------------

To use RepoBee with our Gitea test instance, you need to sign up, create a token
and a target orgnization.

To sign up, click ``Register`` in the top right corner of the home page and
enter the required details. You don't need to use a real email address. For
example, feel free to use ``<YOUR_USERNAME>@repobee.org``.

When signed in, create a token as described in :ref:`gitea_access_token`, and
then create a target organization as described in :ref:`gitea_organization`.
Optionally, you may also create a template organization, but if you're just
playing around, we already provide a public template organization called
`cs1-templates <https://gitea.repobee.org/cs1-templates>`_.

Example configuration
---------------------

To speed up your trying the Gitea instance, here's an example configuration.
Values specified within angle brackets ``<>`` should be replaced with your own
values. See :ref:`config` for how to edit RepoBee's configuration, and then
input the following.

.. code-block:: ini

    user = <YOUR_USERNAME>
    base_url = https://gitea.repobee.org/api/v1
    org_name = <YOUR_TARGET_ORGANIZATION>
    template_org_name = cs1-templates
    token = <YOUR_TOKEN>
    students_file = /path/to/students.txt

Of course, feel free to use your own template organization if you so wish. Here
we just assume that you want to get started as quickly as possible and so use
``cs1-templates``.

You can then use the following ``students.txt``, or any subset of it.

.. code-block:: bash

    alice
    bob
    eve
    steve

While you can have more students if you wish, the demo instance runs on a very
slow server, and so we recommend using a relatively small amount of students in
order to get reasonable performance.

After configuring RepoBee, make sure to run ``config verify`` to check the
configuration for potential problems.

.. hint::

    You can create a "student user" of your own and include in the students
    list, such that you can log in and view the whole thing from the perspective
    of a student.
