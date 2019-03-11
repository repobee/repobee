.. _plugins:

Plugins for ``repomate``
************************
``repomate`` defines a fairly simple but powerful plugin system that allows
programmers to hook into certain execution points. To read more about the
details of these hooks (and how to write your own plugins), see the
`repomate-plug docs`_. Currently, plugins can hook into the ``clone`` command
to perform arbitrary tasks on the cloned repos (such as running test classes),
and the ``assign-reviews`` command, to change the way reviews are
assigned.

.. _configure_plugs:

Using Existing Plugins
======================
You can specify which plugins you want to use either by adding them to the
configuration file, or by specifying them on the command line. Personally,
I find it most convenient to specify plugins on the command line. To do this,
we can use the ``-p|--plug`` option *before* any other options. The reson the
plugins must go before any other options is that some plugins add command line
arguments, and must therefore be parsed separately. As an example, we can
activate the builtins_ ``javac`` and ``pylint`` like this:

.. code-block:: bash

    $ repomate -p pylint -p javac clone -mn master-repo-1 -sf students.txt

This will clone the repos, and the run the plugins on the repos. We can also
specify the default plugins we'd like to use in the configuration file by adding
the ``plugins`` option under the ``[DEFAULT]`` section. Here is an example of
using the builtins_ ``javac`` and ``pylint``.

.. code-block:: bash

    [DEFAULTS]
    plugins = javac, pylint

Like with all other configuration values, they are only used if no command line
options are specified. If you have defaults specified, but want to run without
any plugins, you can use the ``--no-plugins``, which disables plugins.

.. important::

    The order plugins are specified in is significant and implies the execution
    order of the plugins. This is useful for plugins that rely on the results
    of other plugins. This system for deciding execution order may be
    overhauled in the future, if anyone comes up with a better idea.

Some plugins can be further configured in the configuration file by adding
new headers. See the documentation of the specific plugins

.. _built-in _peer review plugins:

Built-in plugins for ``repomate assign-reviews``
=====================================================
``repomate`` ships with two plugins for the ``assign-reviews`` command.  The
first of these is the :py:mod:`~repomate.ext.defaults` plugin, which provides
the default allocation algorithm. As the name suggests, this plugin is loaded
by default, without the user specifying anything. The second plugin is the
:py:mod:`~repomate.ext.pairwise` plugin. This plugin will divide ``N`` students
into ``N/2`` groups of 2 students (and possibly one with 3 students, if ``N``
is odd), and have them peer review the other person in the group. The intention
is to let students sit together and be able to ask questions regarding the repo
they are peer reviewing. To use this allocation algorithm, simply specify the
plugin with ``-p pairwise`` to override the default algorithm. Note that this
plugin ignores the ``--num-reviews`` argument.

.. _builtins:

Built-in Plugins for ``repomate clone``
=======================================
``repomate`` currently ships with two built-in plugins:
:py:mod:`~repomate.ext.javac` and :py:mod:`~repomate.ext.pylint`. The former
attempts to compile all ``.java`` files in each cloned repo, while the latter
runs pylint_ on every ``.py`` file in each cloned repo. These plugins are
mostly meant to serve as demonstarations of how to implement simple plugins in
the ``repomate`` package itself.

``pylint``
----------
The :py:mod:`~repomate.ext.pylint` plugin is fairly simple: it finds all
``.py`` files in the repo, and runs ``pylint`` on them individually.
For each file ``somefile.py``, it stores the output in the file
``somefile.py.lint`` in the same directory. That's it, the
:py:mod:`~repomate.ext.pylint` plugin has no other features, it just does its
thing.

.. important::

    pylint_ must be installed and accessible
    by the script for this plugin to work!

``javac``
---------
The :py:mod:`~repomate.ext.javac` plugin runs the Java compiler program
``javac`` on all ``.java`` files in the repo. Note that it tries to compile
*all* files at the same time.

CLI Option
++++++++++
:py:mod:`~repomate.ext.javac` adds a command line option ``-i|--ignore`` to
``repomate clone``, which takes a space-separated list of files to ignore when
compiling.

Configuration
+++++++++++++
:py:mod:`~repomate.ext.javac` also adds a configuration file option
``ignore`` taking a comma-separated list of files, which must be added under
the ``[javac]`` section. Example:

.. code-block:: bash

    [DEFAULTS]
    plugins = javac

    [javac]
    ignore = Main.java, Canvas.java, Other.java

.. important::

    The :py:mod:`~repomate.ext.javac` plugin requires ``javac`` to be installed
    and accessible from the command line. All ``JDK`` distributions come with
    ``javac``, but you must also ensure that it is on the PATH variable.

.. _external:

External Plugins
================
It's also possible to use plugins that are not included with ``repomate``.
Following the conventions defined in the `repomate-plug docs`_, all plugins
uploaded to PyPi should be named ``repomate-<plugin>``, where ``<plugin>`` is
the name of the plugin and thereby the thing to add to the ``plugins`` option
in the configuration file. Any options for the plugin itself should be
located under a header named ``[<plugin>]``. For example, if I want to use
the `repomate-junit4`_ plugin, I first install it:

.. code-block:: bash

    python3 -m pip install repomate-junit4

and then use for example this configuration file to activate the plugin, and
define some defaults:

.. code-block:: bash

    [DEFAULTS]
    plugins = junit4

    [junit4]
    hamcrest_path = /absolute/path/to/hamcrest-1.3.jar
    junit_path = /absolute/path/to/junit-4.12.jar


.. important::

    If the configuration file exeists, it *must* contain the ``[DEFAULTS]``
    header, even if you don't put anything in that section. This is to minimize
    the risk of subtle misconfiguration errors by novice users. If you only
    want to configure plugins, just add the ``[DEFAULTS]`` header by itself,
    without options, to meet this requirement.

.. _repomate-junit4: https://github.com/slarse/repomate-junit4
.. _repomate-plug: https://github.com/slarse/repomate-plug
.. _pylint: https://www.pylint.org/
.. _repomate-plug docs: https://repomate-plug.readthedocs.io/en/latest/
