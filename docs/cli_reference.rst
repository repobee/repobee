CLI User Guide
**************
This document contains detailed information about all of the CLI commands
offered by ``gits_pet``.

.. important::

    In this section, all output related to the configuration file is
    omitted. See :ref:`Configuration` for details on the configuration
    file.

.. important::

    This section only outlines a high level overview of each of the commands,
    along with example usage. The examples are not guaranteed to be backwards
    compatible with older versions. For detailed usage for your specific
    version, see how to use the help_ option.
    

setup
-----
Put simply, the ``setup`` command sets up student repositories based on master
repositories. In more detail, it roughly does the following:

1. Create one team per student and add the corresponding students to
their teams. If a team already exists, it is left as-is. If a student
is already in its team, nothing happens. If no account exists with the
specified username, the team is created regardless but no one is added
to it.

2. For each master repository, create one student repo per team and add
it to the corresponding student team. If a repository already exists,
it is skipped.

3. Push files from the master repos to the corresponding student repos.

Examples
========

.. code-block:: bash

    $ gits_pet setup -mn master-repo-1 master-repo-2 -sf students.txt 
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: gits-pet-demo
       
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
    [INFO] created gits-pet-demo/eggs-master-repo-1
    [INFO] created gits-pet-demo/ham-master-repo-1
    [INFO] created gits-pet-demo/spam-master-repo-1
    [INFO] created gits-pet-demo/eggs-master-repo-2
    [INFO] created gits-pet-demo/ham-master-repo-2
    [INFO] created gits-pet-demo/spam-master-repo-2
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/ham-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/ham-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/spam-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/eggs-master-repo-2 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/eggs-master-repo-1 master
    [INFO] Pushed files to https://some-enterprise-host/gits-pet-demo/spam-master-repo-2 master

update
------
The ``update`` command pushes the specified master repos to the corresponding
student repos. This is useful if, for example, changes are made to some master
repo after the student repos have been created, and updates need to be pushed.
The command will not *force* updates, meaning that any repos that have commits
that are not on the master repos default branch (i.e. students have made
changes), will not receive updates. Optionally, one can choose to open
an issue in the repos to which pushes fail.

Examples
========

.. code-block:: bash

    $ gits_pet update -mn master-repo-1 master-repo-2 -s spam egg hams
    [INFO] cloning into master repos ...
    [INFO] cloning into file:///path/to/repos/master-repo-1
    [INFO] cloning into file:///path/to/repos/master-repo-2
    [INFO] pushing files to student repos ...
    [INFO] pushing, attempt 1/3
    [INFO] https://gits-15.sys.kth.se/test-tools/a-master-repo-1 is up-to-date
    [INFO] https://gits-15.sys.kth.se/test-tools/b-master-repo-1 is up-to-date
    [INFO] https://gits-15.sys.kth.se/test-tools/c-master-repo-1 is up-to-date
    [INFO] https://gits-15.sys.kth.se/test-tools/a-master-repo-2 is up-to-date
    [INFO] https://gits-15.sys.kth.se/test-tools/b-master-repo-2 is up-to-date
    [INFO] https://gits-15.sys.kth.se/test-tools/c-master-repo-2 is up-to-date
    [INFO] done!




.. _help:

help
----
The ``-h|--help`` option (it is not a command!) can be used to view information
usage information on the command line. This works both for the base
``gits_pet`` command, as well as for all subcommands.

Examples
========

.. code-block:: bash

    $ gits_pet -h
    usage: gits_pet [-h]
                {setup,update,migrate,clone,add-to-teams,open-issue,close-issue,verify-connection}
                ...

    A CLI tool for administrating student repositories.

    positional arguments:
      {setup,update,migrate,clone,add-to-teams,open-issue,close-issue,verify-connection}
        setup               Setup student repos.
        update              Update existing student repos.
        migrate             Migrate master repositories into the target
                            organization.
        clone               Clone student repos.
        add-to-teams        Create student teams and add students to them. This
                            command is automatically executed by the `setup`
                            command.
        open-issue          Open issues in student repos.
        close-issue         Close issues in student repos.
        verify-connection   Verify your settings, such as the base url and the
                            OAUTH token.

    optional arguments:
      -h, --help            show this help message and exit

Or with a command (here, the ``setup`` command):

.. code-block:: bash

    $ gits_pet setup -h
    usage: gits_pet setup [-h] [-u USER]
                      (-sf STUDENTS_FILE | -s STUDENTS [STUDENTS ...])
                      [-o ORG_NAME] [-g GITHUB_BASE_URL] -mn MASTER_REPO_NAMES
                      [MASTER_REPO_NAMES ...]

    Setup student repositories based on master repositories. This command performs
    three primary actions: sets up the student teams, creates one student
    repository for each master repository and finally pushes the master repo files
    to the corresponding student repos. It is perfectly safe to run this command
    several times, as any previously performed step will simply be skipped. The
    master repo is assumed to be located in the target organization, and will be
    temporarily cloned to disk for the duration of the command.

    optional arguments:
      -h, --help            show this help message and exit
      -u USER, --user USER  Your GitHub username. Needed for pushing without CLI
                            interaction.
      -sf STUDENTS_FILE, --students-file STUDENTS_FILE
                            Path to a list of student usernames.
      -s STUDENTS [STUDENTS ...], --students STUDENTS [STUDENTS ...]
                            One or more whitespace separated student usernames.
      -o ORG_NAME, --org-name ORG_NAME
                            Name of the organization to which repos should be
                            added.
      -g GITHUB_BASE_URL, --github-base-url GITHUB_BASE_URL
                            Base url to a GitHub v3 API. For enterprise, this is
                            usually `https://<HOST>/api/v3`
      -mn MASTER_REPO_NAMES [MASTER_REPO_NAMES ...], --master-repo-names MASTER_REPO_NAMES [MASTER_REPO_NAMES ...]
                            One or more names of master repositories. Names must
                            either refer to local directories, or to master
                            repositories in the target organization.
