.. _getting_started:

Getting started
***************

.. important::

    This guide assumes that the user has access to a ``bash``-like shell, or is
    tech-savvy enough to translate the instructions into some other shell
    environment.

.. important::

   Whenever you see specific mentions of GitHub, refer to the :ref:`gitlab`
   section for how this translates to use with GitLab.

The basic workflow of RepoBee is best described by example. This guide will
take you through most of RepoBee's core functionality with using less realistic
examples as the backdrop. In this first section, we will set up everything on
the hosting platform, and configure RepoBee to interface with the hosting
platform. The steps are as follows.

1. Create an organization (the target organization).
2. Configure RepoBee for the target organization.
3. Verify settings.
4. Set up the template repos.

When this initial setup is over and done with, the following parts of the guide
will teach you how to use the most fundamental parts of RepoBee.

Create an organization
======================

This is an absolutely necessary pre-requisite for using RepoBee.
Create an organization with an appropriate name on the platform instance you
intend to use. You can find the ``New organization`` button by going to
``Settings -> Organization``. I will call my *target organization*
``repobee-demo``, so whenever you see that, substitute in the name of your
target organization.

.. important::

    At KTH, we most often do not want our students to be able to see each
    others' repos. By default, however, members have read access to *all*
    repos. To change this, go to the organization dashboard and find your way
    to ``Settings -> Member privileges``. There should be a drop-down called
    something along the lines of "Base permissions" or "Default repository
    settings", which you will want to set to ``None``. The placement and name
    of this drop-down has changed places twice since the first iteration of
    this documentation, so it may not be an exact match, but you should find it
    somewhere around there.

.. _configure_repobee:

RepoBee command structure
=========================

All commands in repobee are ordered in *categories*, each category containing
a set of related *actions*. All core commands are invoked like so.

.. code-block:: bash

    $ repobee <category> <action>

You can view all available categories like so.

.. code-block:: bash
    :caption: RepoBee's top-level help section, listing all categories

    $ repobee -h
    usage: repobee [-h] [-v] {repos,teams,issues,reviews,config,plugin,manage} ...

    A CLI tool for administrating large amounts of git repositories on GitHub and
    GitLab instances. Read the docs at: https://repobee.readthedocs.io

    Loaded plugins: distmanager-3.0.0-beta.1, pluginmanager-3.0.0-beta.1

    positional arguments:
      {repos,teams,issues,reviews,config,plugin,manage}
        repos               manage repositories
        teams               manage teams
        issues              manage issues
        reviews             manage peer reviews
        config              configure RepoBee
        plugin              manage plugins
        manage              manage the RepoBee installation

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         display version info

The categories are listed under the *positional arguments*. To view the actions
available for any one category, simply type ``repobee <category> -h``. As an
example, we can have a look at the ``repos`` category to see the available
actions.

.. code-block:: bash
    :caption: The help section for the repos category

    $ repobee repos -h
    usage: repobee repos [-h] {setup,update,clone,migrate} ...

    Manage repositories.

    positional arguments:
      {setup,update,clone,migrate}
        setup               setup student repos and associated teams
        update              update existing student repos
        clone               clone student repos
        migrate             migrate repositories into the target organization

    optional arguments:
      -h, --help            show this help message and exit

Similarly, to access the help section of a given action, simply type ``repobee
<category> <action> -h``.

.. note::

    If you have followed the instructions from the installer and are using
    ``bash`` or ``zsh``, RepoBee's tab completion should help you significantly
    in navigating the different categories!

.. _config:

Configure RepoBee for the target organization (the ``config`` category)
=======================================================================

In this section, we'll cover the ``config`` category of commands. These are used
to configure RepoBee.

Editing the global configuration file (the ``wizard`` and ``show`` actions)
---------------------------------------------------------------------------

For RepoBee to work at all, it needs to be provided with an access token to
whichever platform instance you intend to use. See the `GitHub access token
docs`_ for how to create a token. The token should have the ``repo`` and
``admin:org`` scopes. You can either set this token in the ``REPOBEE_TOKEN``
environment variable with whatever method you deem appropriate, or you can put
it in the configuration file as described next.

.. note::

   See :ref:`gitlab access token` if you use GitLab!

The ``config wizard`` command starts a configuration wizard that prompts you
for default values for the available settings. The defaults that are set in the
configuration file are *just defaults*, and can always be overridden on the
command line. For the rest of this guide, I will assume that the config file
has defaults for at least the following:

.. code-block:: bash
   :caption: config.ini

   [repobee]
   base_url = https://some-enterprise-host/api/v3
   user = slarse
   org_name = repobee-demo
   template_org_name = template-repos
   token = SUPER_SECRET_TOKEN

Now, run ``repobee config wizard`` and enter your own values for the options
shown above. To skip an option, simply press ENTER without first typing in a
value. Here are some pointers regarding the different values:

* Enter the correct url for your platform instance. There are two options:
    - If you are working with GitHub Enterprise, simply replace
      ``some-enterprise-host`` with the appropriate hostname.
    - If you are working with ``github.com``, replace the whole url
      with ``https://api.github.com``.
* Replace ``slarse`` with your GitHub username.
* Replace ``repobee-demo`` with whatever you named your target organization.
* Replace ``SUPER_SECRET_TOKEN`` with your access token.
* Replace ``template_org_name`` with the name of the organization with your template repos.
    - It you keep the template repos in the target organization or locally, **skip
      this option**.
* **If you are using GitLab**:
    - The ``base_url`` should be to the host, not to the API endpoint. I.e. if
      you are using https://gitlab.com, then the ``base_url`` option should
      simply read ``https://gitlab.com``.

.. note::

    If you use GitLab, you must also activate the GitLab plugin. See
    :ref:`plugins`.

That's it for configuration. The ``show`` action can be used to check that you
got everything set correctly.

.. code-block:: bash

    $ repobee config show
    Found valid config file at /home/slarse/.config/repobee/config.ini
    ----------------BEGIN CONFIG FILE-----------------
    [repobee]
    base_url = https://some-enterprise-host/api/v3
    user = slarse
    org_name = repobee-demo
    template_org_name = template-repos
    token = xxxxxxxxxx
    -----------------END CONFIG FILE------------------

Note that the token is not shown. To show secrets in the configuration file,
provide the ``--secrets`` option to ``config show``. If you ever want to
re-configure some of the options, simply run ``config wizard`` again.

.. _local_config:

Local config files
------------------

When executing a command, RepoBee will first look for a file called
``repobee.ini`` in the current working directory. If such a file is found, it
completely overrides the global config file. This is useful for managing
different courses or groups within courses, with different settings.

The students file
-----------------

Most RepoBee commands allow you to specify the students for whose repos you
want to do something either directly on the command line with the
``--students`` option, or via a file that we refer to as a *students file*.
A default for this file can be set in the config file as the ``students_file``
option, but it can also be provided on the command line with the
``--students-file`` option.

The format of the students file is simple: each line contains a whitespace
separated list of student usernames, and represents a team of students. For
example, the following students file represents single-student teams and would
make for individual tasks.

.. code-block:: bash
   :caption: students.txt

    slarse
    glassey
    glennol

The above file will be assumed to be available as ``students.txt`` throughout
the rest of the user guide.

For group assignments, simply place multiple student usernames on a line to
form a multi-student teams. The following example places ``slarse`` and
``glassey`` in the same team, and ``glennol`` in a separate one.

.. code-block:: bash
    :caption: students.txt

    slarse glassey
    glennol

The order of usernames on a line does not matter; they are always sorted
lexicographically after parsing. See :ref:`groups` for more information on
group assignments.

Verifying the configuration (the ``verify`` action)
---------------------------------------------------

Now that everything is set up, it's time to verify all of the settings. Given
that you have a configuration file that looks something like the one above,
you can simply run the ``config verify`` command without any options.

.. code-block:: bash

    $ repobee config verify
    Verifying settings ...
    Trying to fetch user information ...
    SUCCESS: found user slarse, user exists and base url looks okay
    Verifying access token scopes ...
    SUCCESS: access token scopes look okay
    Trying to fetch organization ...
    SUCCESS: found organization test-tools
    Verifying that user slarse is an owner of organization repobee-demo
    SUCCESS: user slarse is an owner of organization repobee-demo
    Trying to fetch organization template-repos ...
    SUCCESS: found organization template-repos
    Verifying that user slarse is an owner of organization template-repos
    SUCCESS: user slarse is an owner of organization template-repos
    GREAT SUCCESS: All settings check out!

If any of the checks fail, you should be provided with a semi-helpful error
message. When all checks pass and you get ``GREAT SUCCESS``, move on to the next
section!

.. note::

    Less privileged users, such as teaching assistants that have been assigned
    with the :ref:`auto_tamanager` plugin, may see a warning about not being an
    owner of the organization. That's fine and expected, but note that this may
    make them unable to execute certain commands, such as those creating teams
    and repositories.

Set up template repos
=======================

How you do this will depend on where you want to have your template repos. I
recommend having a separate, persistent organization so that you can work on
repos across course rounds. If you already have a template organization with your
template repos set up somewhere, and ``template_org_name`` is specified in the
config, you're good to go. If you need to migrate repos into the target
organization (e.g. if you keep template repos in the target organization), see
the :ref:`migrate` section. For all commands but the ``migrate`` command, the
way you set this up does not matter as far as RepoBee commands go.

.. note::

   Recall that there is nothing special about template repos, they are just your
   templates for student repos. If you have an organization set up with template
   repositories, then that is a viable template organization.

With this initial setup out of the way, it is time to move on to setting up and
managing student repositories in :ref:`repos category`.

.. _Organization: https://help.github.com/articles/about-organizations/
.. _`GitHub access token docs`: https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
