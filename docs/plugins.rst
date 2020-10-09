.. _plugins:

Plugins for RepoBee (the ``plugin`` category)
*********************************************

RepoBee defines a fairly simple but powerful plugin system that allows
programmers to hook into certain execution points. To read more about the
details of these hooks (and how to write your own plugins), see the
:ref:`repobee-plug`.

.. _list of plugins:


Listing available plugins (the ``list`` action)
===============================================

The ``plugin list`` command allows you to list available plugins for RepoBee.
It should look something like this:


.. code-block:: bash
	:caption: Sample output from the ``plugin list`` command

	$ repobee plugin list
	╒═══════════╤══════════════════════════════════════════╤═══════════════════════════════════════════════════════╤══════════╤════════════════╕
	│ Name      │ Description                              │ URL                                                   │ Latest   │ Installed      │
	│           │                                          │                                                       │          │ (√ = active)   │
	╞═══════════╪══════════════════════════════════════════╪═══════════════════════════════════════════════════════╪══════════╪════════════════╡
	│ junit4    │ Plugin for RepoBee that runs JUnit4 on   │ https://github.com/repobee/repobee-junit4             │ v1.0.0   │ v1.0.0         │
	│           │ cloned repos                             │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ feedback  │ A RepoBee plugin for opening feedback    │ https://github.com/repobee/repobee-feedback           │ v0.6.2   │ v0.6.2 √       │
	│           │ issues in on student issue trackers      │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ sanitizer │ A plugin for sanitizing master           │ https://github.com/repobee/repobee-sanitizer          │ v0.1.0   │ -              │
	│           │ repositories before distribution to      │                                                       │          │                │
	│           │ students                                 │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ csvgrades │ A plugin for RepoBee that parses the     │ https://github.com/repobee/repobee-csvgrades          │ v0.2.0   │ -              │
	│           │ JSON file produced by list-issues to     │                                                       │          │                │
	│           │ report grades into a CSV file            │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ gitlab    │ Makes RepoBee compatible with GitLab     │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in       │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ javac     │ Runs javac on student repos after        │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in       │
	│           │ cloning                                  │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ pairwise  │ Makes peer review allocation pairwise    │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in       │
	│           │ (if student A reviews student B, then    │                                                       │          │                │
	│           │ student B reviews student A)             │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ pylint    │ Runs pylint on student repos after       │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in       │
	│           │ cloning                                  │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ query     │ An experimental query command for        │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in       │
	│           │ querying the hooks results file (NOTE:   │                                                       │          │                │
	│           │ This plugin is not stable)               │                                                       │          │                │
	├───────────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────┼──────────┼────────────────┤
	│ tamanager │ Manager plugin for adding and removing   │ https://repobee.readthedocs.io/en/stable/plugins.html │ N/A      │ built-in √     │
	│           │ teachers/teaching assistants from the    │                                                       │          │                │
	│           │ taget organization. Teachers are granted │                                                       │          │                │
	│           │ read access to all repositories in the   │                                                       │          │                │
	│           │ organization. This plugin should not be  │                                                       │          │                │
	│           │ used with GitLab due to performance      │                                                       │          │                │
	│           │ issues. (NOTE: This plugin is not stable │                                                       │          │                │
	│           │ yet and may change without notice)       │                                                       │          │                │
	╘═══════════╧══════════════════════════════════════════╧═══════════════════════════════════════════════════════╧══════════╧════════════════╛

There are a few things to note from the output. First of all, several plugins
are listed as *built-in* in the column labeled ``Installed``. This means that
they ship with RepoBee, and there is no need to install them. Any plugin not
listed as built-in is external, and must be installed as described in the next
section. You may also note a ``√`` next to certain version numbers. This means
that the plugin is *active*, which is discussed in :ref:`activate_plugins`.

.. note::

    **External plugins have separate documentation:** An important thing to
    note about external plugins is that they typically have separate
    documentation on usage. You may find this by visiting the URL listed by the
    ``list`` action.

.. _configure_plugs:

Installing plugins (the ``install`` action)
===========================================

The ``install`` action allows a user to install one of our curated plugins, or
user-made plugins. To install a curated plugin, simply run ``repobee plugin
install``, and a menu system much like the ``config wizard`` will guide you
through the install process. To upgrade a plugin, simply run the ``install``
action again and select a newer version.

The ``install`` action also allows for a *local* install. This is useful if you
want to install an unofficial plugin, or perhaps something that you wrote
yourself. To perform a local install, simply provide the path to the file (if
single-file plugin) or directory (if a packaged plugin) containing the plugin
to the ``--local`` option.

.. code-block:: bash
    :caption: Example of a local plugin install

    $ repobee plugin install --local path/to/plugin

Note that a local install may sometimes be dependent on its location in the
local file system. If you move or delete the local plugin, it may break
RepoBee's installation of it.

Uninstalling plugins (the ``uninstall`` action)
===============================================

To uninstall a plugin, simply run ``repobee plugin uninstall``. This will guide
you through the process of uninstalling any installed plugin.

.. hint::

    Sometimes, plugins break, and may cause RepoBee to fail to load. If you
    experience this, try running ``uninstall`` with the ``--no-plugins``
    preparser option.

    .. code-block:: bash

        $ repobee --no-plugins plugin uninstall

.. _activate_plugins:

Managing installed plugins (the ``activate`` action)
====================================================

A plugin being installed is not enough for it to actually do anything
(otherwise, all of the plugins that ship with RepoBee would always do things).
There are two ways to activate plugins: temporarily and persistently.

Temporary plugin activation
---------------------------

You can activate plugins temporarily for one invocation by specifying them with
the ``--plug|-p`` option to the preparser. For example, if I want to run ``repos
clone`` with the ``javac`` plugin active, I would do something like this:

.. code-block:: bash

    $ repobee -p javac repos clone [...]

We recommend using the ``-p`` preparser option for plugins that you only want to
activate from time to time, but you don't necessarily want them active all the
time.

.. hint::

    You can specify the ``-p`` option multiple times to temporarily activate
    multiple plugins. That is to say, type ``repobee -p javac -p pylint [...]``
    to activate both the ``javac`` and ``pylint`` plugins.

Persistent plugin activation
----------------------------

To persistently activate or deactivate a plugin, RepoBee provides an
``activate`` action. Run ``repobee plugin activate``, and follow the prompts to
activate your desired plugin(s). We recommend activating plugins in this fashion
if they are to be used indefinitely, such as plugins that add commands.

.. note::

    If you use GitLab, you should most definitely run ``plugin activate`` to
    activate the ``gitlab`` plugin permanently!

Plugin configuration
--------------------

Some plugins are configurable, meaning that they read values from the
configuration file. To be able to configure a plugin with the ``config wizard``
command, **the plugin must be active**. It doesn't matter if the plugin is
temporarily or persistently activated. As an example, I can configure the
``javac`` plugin by running the ``config wizard`` like so.

.. code-block:: bash

    $ repobee -p javac config wizard

Plugins typically use sections other than the ``repobee`` section of the
configuration file, and you'll find that new sections pop up in the ``config
wizard`` when certain plugins are active.
