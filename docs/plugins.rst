Plugins for ``repomate clone``
******************************
``repomate`` defines a fairly simple but powerful plugin system that allows
programmers to hook into certain execution points in the ``clone`` command.
The purpose is to be able to execute arbitrary tasks on cloned repos, e.g.
running tests on code or finding the average word length in the repository.
You know. Arbitrary tasks. Plugins can currently hook into the configuration
file, add command line arguments and act on cloned repos. In this section,
we'll walk through how to use existing plugins. If you feel the itch to creatie
your own plugin, head over to the `repomate-plug docs`_!

.. _configure_plugs:

Using Existing Plugins
======================
To use an installed plugin, it must be specified in the :ref:`config` in the
``plugins`` option under the ``[DEFAULT]`` section. Here is an example of using
the builtins_ ``javac`` and ``pylint``.

.. code-block:: bash

    [DEFAULTS]
    plugins = javac, pylint

The order of the plugins is significant and implies the execution order of the
plugins. This is useful for plugins that rely on the results of other plugins.
This system for deciding execution order may be overhauled in the future, if
anyone comes up with a better idea.

.. _builtins:

Built-in Plugins
================
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


.. _repomate-junit4: https://github.com/slarse/repomate-junit4
.. _repomate-plug: https://github.com/slarse/repomate-plug
.. _pylint: https://www.pylint.org/
.. _repomate-plug docs: https://repomate-plug.readthedocs.io/en/latest/
