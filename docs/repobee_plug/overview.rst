Plugin system overview
**********************
Creating plugins for RepoBee is not difficult, and you do not need to be a
seasoned Python developer in order to make something that is genuinely useful.

.. _plug_conventions:

Conventions
===========

For RepoBee to discover a plugin and its hooks, the following conventions
need to be adhered to:

1. The PyPi package should be named ``repobee-<plugin>``, where ``<plugin>``
   is the name of the plugin.
2. The actual Python package (i.e. the directory in which the source files
   are located) should be called ``repobee_<plugin>``. In other words,
   replace the hyphen in the PyPi package name with an underscore.
3. The Python module that defines the plugin's hooks/hook classes should be
   name ``<plugin>.py``.
4. Task plugins that add command line options must prefix the option with
   ``--<plugin>``. So, if the plugin ``exampleplug`` wants to add the option
   ``--ignore``, then it must be called ``--exampleplug-ignore``.

    - The reason for this is to avoid option collisions between different plugins.
    - Note that this does not apply to extension command plugins, as they do
      not piggyback on existing commands.

For an example plugin that follows these conventions, have a look at
repobee-junit4_.  Granted that the plugin follows these conventions and is
installed, it can be loaded like any other RepoBee plugin (see
:ref:`configure_plugs`).

Hooks
=====
There are two types of hooks in RepoBee: *core hooks* and *extension
hooks*.

Core hooks
----------
Core hooks provide core functionality for RepoBee, and always have a default
implementation. Providing a different plugin implementation will override this
behavior, thereby changing some core part of RepoBee. In general, only one
implementation of a core hook will run per invocation of RepoBee. All core hooks
are defined in :py:mod:`repobee_plug._corehooks`.

Extension hooks
---------------
Extension hooks extend the functionality of RepoBee in various ways, for example
by extending the existing commands in RepoBee, or by creating entirely new
commands. These are probably of most interest to most people looking to create
plugins for RepoBee. Unlike the core hooks, there are no default
implementations of the extension hooks, and multiple implementations can be run
on each invocation of RepoBee. All extension hooks are defined in
:py:mod:`repobee_plug._exthooks`.

.. _implementing hooks:

Implementing hook functions
---------------------------
There are two ways to implement hooks: as standalone functions or as methods
wrapped in a :py:class:`~repobee_plug.Plugin` class. In the following two
sections, I will briefly show both approaches. For a comprehensive guide on how
to use these approaches, refer to the :ref:`creating plugins` section.

.. _standalone hook functions:

Standalone hook functions
+++++++++++++++++++++++++
Hook functions can be implemented as standalone functions by decorating them
with the :py:func:`~repobee_plug.repobee_hook` decorator. For example, if we
wanted to implement the ``post_clone`` hook, we could do it like this:

.. code-block:: python
    :caption: exampleplug.py

    import repobee_plug as plug

    @plug.repobee_hook
    def post_clone(path, api):
        """Return a useless Task."""
        print(path)

This function will be called once for each cloned repository after RepoBee has
finished cloning all repositories with the ``clone`` command. This particular
implementation will simply print the path to each cloned repository.

The ``clone_task`` hook is described in more detail in :ref:`creating plugins`.
For a complete plugin written with this approach, see the `repobee-gofmt plugin
<https://github.com/slarse/repobee-gofmt>`_.

.. _plugin class:

Hook functions in a plugin class
++++++++++++++++++++++++++++++++
Wrapping hook implementations in a class inheriting from
:py:class:`~repobee_plug.Plugin` is recommended way to write plugins for
RepoBee that are in any way complicated. A plugin class is instantiated exactly
once, and that instance then persists throughout the execution of one RepoBee
command, making it a convenient way to implement plugins that require command
line options or any form of state. The :py:class:`~repobee_plug.Plugin` class
also performs some sanity checks when a subclass is defined to make sure that
all public functions have hook function names, which comes in handy if you are
in the habit of misspelling stuff (aren't we all?). Doing it this way,
``exampleplug.py`` would look like this:

.. code-block:: python
    :caption: exampleplug.py

    import repobee_plug as plug

    PLUGIN_NAME = 'exampleplug'

    class ExamplePlugin(plug.Plugin):
        """Example plugin that implements the clone_task hook."""

        def post_clone(self, path, api):
            """Return a useless Task."""
            print(path)

Note how the ``post_clone`` function now does not have the `@plug.repobee_hook`
decorator and that the ``self`` argument was added to it, as it is now a method
of the ``ExamplePlugin`` class. For a complete example of a plugin written with
this approach, see the `repobee-junit4`_ plugin.

.. _repobee-junit4: https://github.com/repobee/repobee-junit4
.. _javac plugin: https://github.com/repobee/repobee/blob/master/repobee/ext/javac.py
.. _pylint plugin: https://github.com/repobee/repobee/blob/master/repobee/ext/pylint.py

.. _repobee-junit4: https://github.com/repobee/repobee-junit4
