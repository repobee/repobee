.. _getting_started:

Getting started (the ``show-config``, ``verify-settings`` and ``setup`` commands)
*********************************************************************************
.. important::

    This guide assumes that the user has access to a ``bash`` shell, or is
    tech-savvy enough to translate the instructions into some other shell
    environment.

.. important::

   Whenever you see specific mentions of GitHub, refer to the :ref:`gitlab`
   section for how this translates to use with GitLab.

The basic workflow of RepoBee is best described by example. In this section,
I will walk you through how to set up a target organization with master and
student repositories by showing every single step I would perform myself. The
basic workflow can be summarized in the following steps:

1. Create an organization (the target organization).
2. Configure RepoBee for the target organization.
3. Verify settings.
4. Set up the master repos.
5. Set up the student repos.

This should leave you with enough knowledge to use the rudimentary features of
RepoBee. There is much more to RepoBee, such as opening/closing issues,
updating student repos and cloning repos in batches. This is covered in later
sections, but you don't necessarily need to go through the entire guide in one
go. Now, let's delve into the above steps in greater detail.

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
    to ``Settings -> Member privileges``. At the very bottom, there should be a
    section called ``Default repository permission``.  Set this to ``None`` to
    disallow students from viewing each others' repos unless explicitly given
    permission by an organization owner (e.g. you).

.. _configure_repobee:

Configure RepoBee for the target organization (``show-config`` and ``verify-settings``)
=======================================================================================
For the tool to work at all, it needs to be provided with an OAUTH2 token to
whichever platform instance you intend to use. See the `GitHub OAUTH docs`_ for
how to create a token. The token should have the ``repo`` and ``admin:org``
scopes. While we can set this token in an environment variable (see
:ref:`configuration`), it's more convenient to just put it in the configuration
file, as we will put other default values in there. We can use the
``show-config`` command to figure out where to put the config file.

.. code-block:: bash

    $ repobee show-config
    [ERROR] FileError: no config file found, expected location: /home/USERNAME/.config/repobee/config.cnf

``show-config`` will check that the configuration file exists and is
syntactically correct. Here, the error message is telling us that it expected
a config file at ``/home/USERNAME/.config/repobee/config.cnf``, so let's add
one there. It should look something like this:

.. code-block:: bash

    [DEFAULTS]
    base_url = https://some-enterprise-host/api/v3
    user = slarse
    org_name = repobee-demo
    master_org_name = master-repos
    token = SUPER_SECRET_TOKEN

Now, you need to substitute in some of your own values in place of mine.

* Enter the correct url for your platform instance. There are two options:
    - If you are working with an enterprise instance, simply replace
      ``some-enterprise-host`` with the appropriate hostname.
    - If you are working with ``github.com``, replace the whole url
      with ``https://api.github.com``.
* Replace ``slarse`` with your GitHub username.
* Replace ``repobee-demo`` with whatever you named your target organization.
* Replace ``SUPER_SECRET_TOKEN`` with your OAUTH token.
* Replace ``master_org_name`` with the name of the organization with your master
  repos.
  - It you keep the master repos in the target organization or locally, **remove
  this option entirely**.

That's it for configuration, and we can check that the file is correctly found
and parsed by running ``show-config`` again:

.. code-block:: bash

    $ repobee show-config
    [INFO] found valid config file at /home/slarse/.config/repobee/config.cnf
    [INFO]
    ----------------BEGIN CONFIG FILE-----------------
    [DEFAULTS]
    base_url = https://some-enterprise-host/api/v3
    user = slarse
    org_name = repobee-demo
    master_org_name = master-repos
    token = SUPER_SECRET_TOKEN
    -----------------END CONFIG FILE------------------

Verify settings
===============
Now that everything is set up, it's time to verify all of the settings. Given
that you have a configuration file that looks something like the one above,
you can simply run the ``verify-settings`` command without any options.

.. code-block:: bash

    $ repobee verify-settings
    [INFO] verifying settings ...
    [INFO] trying to fetch user information ...
    [INFO] SUCCESS: found user slarse, user exists and base url looks okay
    [INFO] verifying oauth scopes ...
    [INFO] SUCCESS: oauth scopes look okay
    [INFO] trying to fetch organization ...
    [INFO] SUCCESS: found organization test-tools
    [INFO] verifying that user slarse is an owner of organization repobee-demo
    [INFO] SUCCESS: user slarse is an owner of organization repobee-demo
    [INFO] trying to fetch organization master-repos ...
    [INFO] SUCCESS: found organization master-repos
    [INFO] verifying that user slarse is an owner of organization master-repos
    [INFO] SUCCESS: user slarse is an owner of organization master-repos
    [INFO] GREAT SUCCESS: All settings check out!

If any of the checks fail, you should be provided with a semi-helpful error
message. When all checks pass and you get ``GREAT SUCCESS``, move on to the
next section!

Set up master repos
=======================
How you do this will depend on where you want to have your master repos. I
recommend having a separate, persistent organization so that you can work on
repos across course rounds. If you already have a master organization with your
master repos set up somewhere, and ``master_org_name`` is specified in the
config, you're good to go. If you need to migrate repos into the target
organization (e.g. if you keep master repos in the target organization), see
the :ref:`migrate` section. For all commands but the ``migrate`` command, the
way you set this up does not matter as far as RepoBee commands go.

.. _setup:

Set up student sepositories
===========================
Now that the master repos are set up, it's time to create the student repos.
While student usernames *can* be specified on the command line, it's often
convenient to have them written down in a file instead. Let's pretend I have
three students with usernames ``slarse``, ``glassey`` and ``glennol``. I'll simply create
a file called ``students.txt`` and type each username on a separate line.

.. code-block:: bash
   :caption: students.txt

    slarse
    glassey
    glennol

.. note::

   **Since v1.3.0:** It is now possible to specify groups of students to get
   access to the same repos by putting multiple usernames on the same line,
   separated by spaces. For example, the following file will put `slarse` and
   `glassey` in the same group.

   .. code-block:: bash

      slarse glassey
      glennol

   See :ref:`groups` for details.

An absolute file path to this file can be added to the config file with the
``students_file`` option (see :ref:`config`). Now, I want to create one student
repo for each student and master repo. The repo names will be on the form
``<username>-<master-repo-name>``, guaranteeing their uniqueness. Each student
will also be added to a team (which bears the same name as the student's user),
and it is the team that is allowed access to the student's repos, and not the
student's actual user. That all sounded fairly complex, but again, it's as
simple as issuing a single command with RepoBee.

.. code-block:: bash

    $ repobee setup -mn master-repo-1 master-repo-2 -sf students.txt
    [INFO] Cloning into master repos ...
    [INFO] Cloning into file:///home/slarse/tmp/master-repo-1
    [INFO] Cloning into file:///home/slarse/tmp/master-repo-2
    [INFO] Created team glennol
    [INFO] Created team glassey
    [INFO] Created team slarse
    [INFO] Adding members glennol to team glennol
    [WARNING] user glennol does not exist
    [INFO] Adding members glassey to team glassey
    [INFO] Adding members slarse to team slarse
    [INFO] Creating student repos ...
    [INFO] Created repobee-demo/glennol-master-repo-1
    [INFO] Created repobee-demo/glassey-master-repo-1
    [INFO] Created repobee-demo/slarse-master-repo-1
    [INFO] Created repobee-demo/glennol-master-repo-2
    [INFO] Created repobee-demo/glassey-master-repo-2
    [INFO] Created repobee-demo/slarse-master-repo-2
    [INFO] Pushing files to student repos ...
    [INFO] Pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glassey-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glassey-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/slarse-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glennol-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/glennol-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repobee-demo/slarse-master-repo-2 master

Note that there was a ``[WARNING]`` message for the username ``glennol``: the user
does not exist. At KTH, this is common, as many (sometimes most) first-time
students will not have created their GitHub accounts until sometime after the
course starts.  These students will still have their repos created, but the
users need to be added to their teams at a later time (to do this, simply run
the ``setup`` command again for these students, once they have created
accounts). This is one reason why we use teams for access privileges: it's
easy to set everything up even when the students have yet to create their
accounts (given that their usernames are pre-determined).

And that's it, the organization is primed and the students should have access
to their repositories!

.. _Organization: https://help.github.com/articles/about-organizations/
.. _`GitHub OAUTH docs`: https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
