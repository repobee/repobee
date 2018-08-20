.. _getting_started:

Getting Started (the ``verify-connection``, ``migrate`` and ``setup`` commands)
*******************************************************************************
.. important::

    This guide assumes that the user has access to a ``bash`` shell, or is
    tech-savvy enough to translate the instructions into some other shell
    environment.

The basic workflow of ``repomate`` is best described by example. In this section,
I will walk you through how to set up an Organization_ with master and student
repositories by showing every single step I would perform myself. The basic
workflow can be summarized in the following steps:

1. Create an organization (the target organization).
2. Configure ``repomate`` for the target organization.
3. Verify settings.
4. Migrate master repositories into the target organization.
5. Create one copy of each master repo for each student.

There is more to ``repomate``, such as opening/closing issues, updating student
repos and cloning repos in batches, but here we will just look at the bare
minimum to get started. Now, let's delve into these steps in greater detail.

Create an Organization
======================
This is an absolutely necessary pre-requisite for using ``repomate``.
Create an organization with an appropriate name on the GitHub instance you
intend to use. You can find the ``New organization`` button by going to
``Settings -> Organization``. I will call my *target organization*
``repomate_demo``, so whenever you see that, substitute in the name of your
target organization.

.. important::

    At KTH, we most often do not want our students to be able to see each
    others' repos. By default, however, members have read access to *all*
    repos. To change this, go to the organization dashboard and find your way
    to ``Settings -> Member privileges``. At the very bottom, there should be a
    section called ``Default repository permission``.  Set this to ``None`` to
    disallow students from viewing each others' repos unless explicitly given
    permission by an organization owner (e.g. you).

Configure ``repomate`` For the Target Organization
==================================================
For the tool to work at all, an environment variable called ``REPOMATE_OAUTH``
must contain an OAUTH2 token to whichever GitHub instance you intend to use.
See the `GitHub OAUTH docs`_ for how to create a token. The token should have
the ``repo`` and ``admin:org`` scopes. Setting the token is easy in ``bash``.
Just add the following line to your ``bash`` config file (``~/.bashrc`` on most
Linux distros, and ``~/.bash_profile`` on OSX).

.. code-block:: bash
    
    export REPOMATE_OAUTH=<SUPER SECRET TOKEN>

When that's added, either source the file with ``source path/to/bash/config``
or simply start another ``bash`` shell, which will automatically read the
file. Verify that the token is there by typing:

.. code-block:: bash

    $ echo $REPOMATE_OAUTH

You should see your token in the output. 

.. note::

    Whenever you see a ``$`` sign preceeding a line in a code block, you are meant
    to type what's *after* the ``$`` sign into your shell. Here, you should type
    only ``echo $REPOMATE_OAUTH``, for example.

With that out of the way, let's create a configuration file We can now use
``repomate`` to figure out where it should be located.

.. code-block:: bash
    
    $ repomate -h
    [INFO] no config file found. Expected config file location: /home/USERNAME/.config/repomate/config.cnf

    <HELP MESSAGE OMITTED>

At the very top, you will find the expected config file location. The exact
path will vary depending on operating system and username. Let's add a
configuration file with the following contents:

.. code-block:: bash

    [DEFAULTS]
    github_base_url = https://some-enterprise-host/api/v3
    user = slarse
    org_name = repomate-demo

Now, you need to substitute in some of your own values in place of mine.

* Enter the correct url for your GitHub instance. There are two options:
    - If you are working with an enterprise instance, simply replace
      ``some-enterprise-host`` with the appropriate hostname.
    - If you are working with ``github.com``, replace the whole url
      with ``https://api.github.com``.
* Replace ``slarse`` with your GitHub username.
* Replace ``repomate-demo`` with whatever you named your target organization.

That's it for configuration, and we can check that the file is correctly found
and parsed by running ``repomate -h`` again.

.. code-block:: bash

    $ repomate -h
    [INFO] config file defaults:

        github_base_url: https://some-enterprise-host/api/v3
        user: slarse
        org_name: repomate-demo

    <HELP MESSAGE OMITTED>

The ``[INFO] config file defaults:`` message (along with the defaults) will pop
up on every ``repomate`` command. I should note that the configuration file
isn't strictly necessary, but it will save us the hassle of typing in the url,
username and organization name on every single command to ``repomate``.

Verify Settings
===============
Now that everything is set up, it's time to verify all of the settings. Given
that you have a configuration file that looks something like the one above,
you can simply run the ``verify-settings`` command without any options.

.. code-block:: bash

    $ repomate verify-settings
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] verifying settings ...
    [INFO] trying to fetch user information ...
    [INFO] SUCCESS: found user slarse, user exists and base url looks okay
    [INFO] verifying oauth scopes ...
    [INFO] SUCCESS: oauth scopes look okay
    [INFO] trying to fetch organization ...
    [INFO] SUCCESS: found organization test-tools
    [INFO] verifying that user slarse is an owner of organization repomate-demo
    [INFO] SUCCESS: user slarse is an owner of organization repomate-demo
    [INFO] GREAT SUCCESS: All settings check out!

If any of the checks fail, you should be provided with a semi-helpful error
message. When all checks pass and you get ``GREAT SUCCESS``, move on to the
next section!

Migrate Master Repositories Into the Target Organization
========================================================
This step sounds complicated, but it's actually very easy, and can be performed
with a single ``repomate`` command. There is however a pre-requisite that must
be fulfilled. You must either

* Have local copies of your master repos.

or

* Have all master repos in the same GitHub instance as your target organization.

Assuming we have the repos ``master-repo-1`` and ``master-repo-2`` in the
current working directory (i.e. local repos), all we have to do is this:

.. code-block:: bash

    $ repomate migrate -mn master-repo-1 master-repo-2
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] created team master_repos
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] created repomate-demo/master-repo-1
    [INFO] created repomate-demo/master-repo-2
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/master-repo-2 master
    [INFO] done!

There are a few things to note here. First of all, the team ``master_repos`` is
created. This only happens the first time ``migrate`` is run on a new
organization. As the name suggests, this team houses all of the master repos.
Each master repo that is migrated with the ``migrate`` command is added to this
team, so they can easily be found at a later time. It may also be confusing that
the local repos are being cloned (into a temporary directory). This is simply
an implementation detail that does not need much thinking about. Finally, the
local repos are pushed to the ``master`` branch of the remote repo. This command
is perfectly safe to run several times, in case you think you missed something.
Running the same thing again yields the following output:


.. code-block:: bash

    $ repomate migrate -mn master-repo-1 master-repo-2
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] cloning into file:///some/directory/path/master-repo-1
    [INFO] cloning into file:///some/directory/path/master-repo-2
    [INFO] repomate-demo/master-repo-1 already exists
    [INFO] repomate-demo/master-repo-2 already exists
    [INFO] pushing, attempt 1/3
    [INFO] https://some-enterprise-host/repomate-demo/master-repo-1 master is up-to-date
    [INFO] https://some-enterprise-host/repomate-demo/master-repo-2 master is up-to-date
    [INFO] done!

In fact, all ``repomate`` commands that deal with pushing to or cloning from
repos in some way are safe to run over and over. This is mostly because of
how ``git`` works, and has little to do with ``repomate`` itself. Now that
our master repos are migrated, we can move on to setting up the student repos!

.. note::

    The ``migrate`` command can also be used to migrate repos from somewhere
    on the GitHub instance into the target organization. To do this, use the
    ``-mu`` option and provide the urls, instead of ``-mn`` with local paths.
    For example, given a repo at
    ``https://some-enterprise-host/other-org/master-repo-1``, it can be
    migrated into ``repomate-demo`` by typing

    .. code-block:: bash

        $ repomate migrate -mu https://some-enterprise-host/other-org/master-repo-1

.. _setup:

Setup Student Repositories
==========================
Now that the master repos have been added to the target organization, it's time
to create the student repos. While student usernames *can* be specified on the
command line, it's often convenient to have them written down in a file
instead. Let's pretend I have three students with usernames ``spam``, ``ham``
and ``eggs``. I'll simply create a file called ``students.txt`` and type each
username on a separate line.

.. code-block:: bash

    spam
    ham
    eggs

I want to create one student repo for each student per master repo. The repo
names will be on the form ``<username>-<master-repo-name>``, guaranteeing their
uniqueness. Each student will also be added to a team (which bears the same
name as the student's user), and it is the team that is allowed access to the
student's repos, and not the student's actual user. That all sounded fairly
complex, but again, it's as simple as issuing a single command with
``repomate``.

.. code-block:: bash
    
    $ repomate setup -mn master-repo-1 master-repo-2 -sf students.txt 
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] cloning into master repos ...
    [INFO] cloning into file:///home/slarse/tmp/master-repo-1
    [INFO] cloning into file:///home/slarse/tmp/master-repo-2
    [INFO] created team eggs
    [INFO] created team ham
    [INFO] created team spam
    [INFO] adding members eggs to team eggs
    [WARNING] user eggs does not exist
    [INFO] adding members ham to team ham
    [INFO] adding members spam to team spam
    [INFO] creating student repos ...
    [INFO] created repomate-demo/eggs-master-repo-1
    [INFO] created repomate-demo/ham-master-repo-1
    [INFO] created repomate-demo/spam-master-repo-1
    [INFO] created repomate-demo/eggs-master-repo-2
    [INFO] created repomate-demo/ham-master-repo-2
    [INFO] created repomate-demo/spam-master-repo-2
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/ham-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/ham-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/spam-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/eggs-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/eggs-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/repomate-demo/spam-master-repo-2 master

Note that there was a ``[WARNING]`` message for the username ``eggs``: the user
does not exist. At KTH, this is common, as many (sometimes most) first-time
students will not have created their GitHub accounts until sometime after the
course starts.  These students will still have their repos created, but the
users need to be added to their teams at a later time (for example with the
``repomate add-to-teams`` command). This is one reason for why we use teams for
access privileges: it's easy to set everything up even when the students have
yet to create their accounts (given that their usernames are pre-determined).

And that's it, the organization is primed and the students should have access
to their repositories!

.. _Organization: https://help.github.com/articles/about-organizations/
.. _`GitHub OAUTH docs`: https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
