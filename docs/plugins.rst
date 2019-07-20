.. _plugins:

Plugins for ``repobee``
************************
RepoBee defines a fairly simple but powerful plugin system that allows
programmers to hook into certain execution points. To read more about the
details of these hooks (and how to write your own plugins), see the
`repobee-plug docs`_.

.. _configure_plugs:

Using Existing Plugins
======================
You can specify which plugins you want to use either by adding them to the
configuration file, or by specifying them on the command line. Personally,
I find it most convenient to specify plugins on the command line. To do this,
use ``-p|--plug`` option *before* any other options. The reson the plugins must
go before any other options is that some plugins alter the command line
interface of RepoBee, and must therefore be parsed separately. As an example,
you can activate the builtins_ ``javac`` and ``pylint`` like this:

.. code-block:: bash

    $ repobee -p pylint -p javac clone -mn master-repo-1 -sf students.txt

This will clone the repos, and the run the plugins on the repos. You can also
specify the default plugins you would like to use in the configuration file by
adding the ``plugins`` option under the ``[DEFAULT]`` section. Here is an
example of using the builtins_ ``javac`` and ``pylint``.

.. code-block:: bash

    [DEFAULTS]
    plugins = javac, pylint

Like with all other configuration values, they are only used if no command line
options are specified. If you have defaults specified, but want to run without
any plugins, you can use the ``--no-plugins`` argument, which disables plugins.

.. important::

    The order plugins are specified in is significant and defines the execution
    order of the plugins. This is useful for plugins that rely on the results
    of other plugins. This system for deciding execution order may be
    overhauled in the future, if anyone comes up with a better idea.

Some plugins can be further configured in the configuration file by adding new
headers. See the documentation of the specific plugins for details on that.

.. _builtins:

Built-in API plugins
====================
RepoBee ships with two API plugins, one for GitHub
(:py:mod:`repobee.ext.github`) and one for GitLab
(:py:mod:`repobee.ext.gitlab`). The GitHub plugin is loaded by default. If you
use GitLab, you must specify the ``gitlab`` plugin either on the command line
or in the configuration file.

Built-in subcommand plugins
===========================
The ``config-wizard`` command is actually a plugin, which loads by default.
It's mostly implemented as a plugin for demonstrational purposes, showing how
to add a command to RepoBee. See :py:mod:`repobee.ext.configwizard` for the
source code.

Built-in plugins for ``repobee assign-reviews``
=====================================================
RepoBee ships with two plugins for the ``assign-reviews`` command.  The
first of these is located in the :py:mod:`~repobee.ext.defaults` plugin, and
just randomly allocates student to review each other. The second plugin is the
:py:mod:`~repobee.ext.pairwise` plugin. This plugin will divide ``N`` students
into ``N/2`` groups of 2 students (and possibly one with 3 students, if ``N``
is odd), and have them peer review the other person in the group. The intention
is to let students sit together and be able to ask questions regarding the repo
they are peer reviewing. To use this allocation algorithm, simply specify the
plugin with ``-p pairwise`` to override the default algorithm. Note that this
plugin ignores the ``--num-reviews`` argument.


Built-in Plugins for ``repobee clone``
=======================================
RepoBee currently ships with two built-in plugins:
:py:mod:`~repobee.ext.javac` and :py:mod:`~repobee.ext.pylint`. The former
attempts to compile all ``.java`` files in each cloned repo, while the latter
runs pylint_ on every ``.py`` file in each cloned repo. These plugins are
mostly meant to serve as demonstarations of how to implement simple plugins in
the ``repobee`` package itself.

``pylint``
----------
The :py:mod:`~repobee.ext.pylint` plugin is fairly simple: it finds all
``.py`` files in the repo, and runs ``pylint`` on them individually.
For each file ``somefile.py``, it stores the output in the file
``somefile.py.lint`` in the same directory. That's it, the
:py:mod:`~repobee.ext.pylint` plugin has no other features, it just does its
thing.

.. important::

    pylint_ must be installed and accessible
    by the script for this plugin to work!

``javac``
---------
The :py:mod:`~repobee.ext.javac` plugin runs the Java compiler program
``javac`` on all ``.java`` files in the repo. Note that it tries to compile
*all* files at the same time.

CLI Option
++++++++++
:py:mod:`~repobee.ext.javac` adds a command line option ``-i|--ignore`` to
``repobee clone``, which takes a space-separated list of files to ignore when
compiling.

Configuration
+++++++++++++
:py:mod:`~repobee.ext.javac` also adds a configuration file option
``ignore`` taking a comma-separated list of files, which must be added under
the ``[javac]`` section. Example:

.. code-block:: bash

    [DEFAULTS]
    plugins = javac

    [javac]
    ignore = Main.java, Canvas.java, Other.java

.. important::

    The :py:mod:`~repobee.ext.javac` plugin requires ``javac`` to be installed
    and accessible from the command line. All ``JDK`` distributions come with
    ``javac``, but you must also ensure that it is on the PATH variable.

.. _external:

External Plugins
================
It's also possible to use plugins that are not included with RepoBee.
Following the conventions defined in the `repobee-plug docs`_, all plugins
uploaded to PyPi should be named ``repobee-<plugin>``, where ``<plugin>`` is
the name of the plugin and thereby the thing to add to the ``plugins`` option
in the configuration file. Any options for the plugin itself should be
located under a header named ``[<plugin>]``. For example, if I want to use
the `repobee-junit4`_ plugin, I first install it:

.. code-block:: bash

    python3 -m pip install repobee-junit4

and then use for example this configuration file to activate the plugin, and
define some defaults:

.. code-block:: bash

    [DEFAULTS]
    plugins = junit4

    [junit4]
    hamcrest_path = /absolute/path/to/hamcrest-1.3.jar
    junit_path = /absolute/path/to/junit-4.12.jar


.. important::

    If the configuration file exists, it *must* contain the ``[DEFAULTS]``
    header, even if you don't put anything in that section. This is to minimize
    the risk of subtle misconfiguration errors by novice users. If you only
    want to configure plugins, just add the ``[DEFAULTS]`` header by itself,
    without options, to meet this requirement.

.. _repobee-junit4: https://github.com/repobee/repobee-junit4
.. _repobee-plug: https://github.com/repobee/repobee-plug
.. _pylint: https://www.pylint.org/
.. _repobee-plug docs: https://repobee-plug.readthedocs.io/en/latest/
