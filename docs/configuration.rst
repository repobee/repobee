.. _configuration:

Configuration
*************
``gits_pet`` *must* be configured with a mandatory environment variable (see
oauth_). Additionally, some of the command line parameters can be
pre-configured with e.g. the GitHub instances' API url and the target
organization's name (see `config`_).

.. _oauth:

GITS_PET_OAUTH Environment Variable
===================================
For the tool to work at all, an environment variable called ``GITS_PET_OAUTH``
must contain an OAUTH2 token to whichever GitHub instance you intend to use.
See the `GitHub OAUTH docs`_ for how to create a token. The token should
have the ``repo`` and ``admin:org`` scopes. Once you have the token, you should
set the environment variable. In a ``bash`` terminal, this can be done with the
command ``export GITS_PET_OAUTH=<YOUR TOKEN>``, where ``<YOUR TOKEN>`` is
replaced with the token. If the token is not properly set, an error message
will be shown when trying to run ``gits_pet``.

.. _config:

Configuration File
==================
An optional configuration file can be added, which specifies default values for
the `--github_base_url`, `--org_name`, `--user` and `--students-list` command
line options. This is especially useful for teachers who are managing repos for
a single course (and, as a consequence, a single organization).

.. code-block:: bash

    [DEFAULTS]
    github_base_url = https://some-api-v3-url
    user = YOUR_USERNAME
    org_name = ORGANIZATION_NAME
    students_file = STUDENTS_FILE_ABSOLUTE_PATH

**To find out where to place the configuration file (and what to name it)**,
run `gits_pet -h`. At the very top, there should be a line looking something
like this:

.. code-block:: bash

    [INFO] no config file found. Expected config file location: /home/USERNAME/.config/gits_pet/config.cnf

The filepath at the end is where you should put your config file.

.. important::

    Do note that the configuration file contains only default values. Specifying
    any of the parameters on the command line will override the configuration
    file's values.

.. _`GitHub OAUTH docs`: https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
