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
4. :ref:`command_extensions` that add command line arguments must use a
   ``--<plugin>`` prefix. So, if the plugin ``exampleplug`` wants to add the
   option ``--ignore``, then it must be called ``--exampleplug-ignore``.

    - The reason for this is to avoid option collisions between different plugins.
    - Note that this does not apply to extension command plugins, as they do
      not piggyback on existing commands.

For an example plugin that follows these conventions, have a look at
repobee-junit4_.  Granted that the plugin follows these conventions and is
installed, it can be loaded like any other RepoBee plugin (see
:ref:`configure_plugs`).

Single-file plugins
===================

RepoBee 3 adds the possibility to creating *single-file plugins*, which are
precisely what it sounds like; a single Python file containing a plugin.
This is very useful in order to try out ideas and just experiment with the
plugin system. There are no particular requirements on the file, other than
the fact that the name of the file must be a valid Python identifier (so, no
spaces!). The name of the file will be the name of the plugin.

.. _repobee-junit4: https://github.com/repobee/repobee-junit4
