.. _gitea:

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

.. _gitea_access_token:

Getting an access token for Gitea
---------------------------------

To create a personal access token for a Gitea instance, log in and then click
your profile picture in the top right corner. From there, click ``Settings``
and then go to the ``Applications`` menu.  At the top you'll find a small
section for generating a new token.

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
