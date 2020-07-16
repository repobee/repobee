.. _creating plugins:

Creating plugins
****************

Creating plugins for RepoBee is easy, there is even a template that will start
you off with a fully functioning plugin! In this section, I will show you
everything you need to know to create task and extension command plugins. Before
we begin, you will need to install `cookiecutter
<https://github.com/cookiecutter/cookiecutter>`_.

.. code-block:: bash

    $ python3 -m pip install --user --upgrade cookiecutter

With this, we will be able to use the `repobee-plugin-cookiecutter template
<https://github.com/repobee/repobee-plugin-cookiecutter>`_ to get starter code
both for basic and advanced plugins, with minimal effort.

.. note::

    In all of the examples in this tutorial, I will use the plugin name
    ``exampleplug``. This is provided to the template as the ``plugin_name``
    option. Wherever you see ``exampleplug`` in file names, command line
    options, configuration files etc, ``exampleplug`` will be replaced by
    whatever you provide for the ``plugin_name`` opiton.

Creating task plugins
=====================
Most plugins for RepoBee are task plugins. The basic idea is that you write some
code for doing something (pretty much anything) in a repository, and RepoBee
scales your code to operate on any number of student or master repositories.
There are currently two types of tasks:

* **Clone task**: operates on student repositories after they have been
  cloned with the ``clone`` command.

* **Setup task**: operates on master repositories before they are pushed to
  student repositories in the ``setup`` and ``update`` commands.

  - Currently, a setup task is not allowed to alter the contents of the master
    Git repository (e.g. with ``git commit``), but plans are in motion for
    allowing this in RepoBee 3.

A task is defined with the :py:class:`~repobee_plug.Task` data structure, and is
more or less just a container for a bunch of callback functions. This allows you
as a plugin creator to implement your tasks however you want. Want to just have
standalone functions? That's fine. Want to use a class? Also works great.

Whether the task you create is a clone task or a setup task is decided by which
hook function(s) you implement. For example, if you implement the
:py:meth:`~repobee_plug._exthooks.TaskHooks.clone_task` hook to return your
task, then you've got a clone task, and if you implement the
:py:meth:`~repobee_plug._exthooks.TaskHooks.setup_task` hook you've got a setup
task. There's no problem implementing both hooks if your task makes sense as
both a clone task and a setup task. Let's have a look at a basic task to get an
idea for how it works.

.. _basic task:

Basic
-----
A basic task plugin can be generated with cookiecutter using the
``repobee-plugin-cookiecutter`` template. Below is a CLI trace of generating
one, which you can follow along with. Of course, replace any personal
information with your own.

.. note::

    Things such as your name and email are only put into local files (most
    notably into ``setup.py`` and ``LICENSE``). It's not actually sent anywhere.

.. code-block:: bash
    :caption: Generating a basic task plugin

    $ python3 -m cookiecutter gh:repobee/repobee-plugin-cookiecutter
    author []: Simon Larsén
    email []: slarse@slar.se
    github_username []: slarse
    plugin_name []: exampleplug
    short_description []: An example task plugin
    Select generate_basic_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]: 2
    Select generate_advanced_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    $ ls
    repobee-exampleplug

After the command has been run, you should have a basic plugin defined locally
in the ``repobee-exampleplug`` directory. Let's have a look at what we got.

.. code-block:: bash

    $ tree repobee-exampleplug
    repobee-exampleplug/
    ├── LICENSE
    ├── README.md
    ├── repobee_exampleplug
    │   ├── exampleplug.py
    │   ├── __init__.py
    │   └── __version.py
    ├── setup.py
    └── tests
            └─test_exampleplug.py

Note how the directory structure adheres to the conventions defined in
:ref:`conventions`. The actual plugin is contained entirely in
``repobee_exampleplug/exampleplug.py``, and this is where you want to make
changes to alter the behavior of the plugin. Let's have a look at it.

.. code-block:: python
    :caption: exampleplug.py (note that docstrings have been removed for brevity)

    import pathlib
    import os

    import repobee_plug as plug

    PLUGIN_NAME = "exampleplug"

    def act(path: pathlib.Path, api: plug.API):
        filepaths = [
            str(p) for p in path.resolve().rglob("*") if ".git" not in str(p).split(os.sep)
        ]
        output = os.linesep.join(filepaths)
        return plug.Result(name=PLUGIN_NAME, status=plug.Status.SUCCESS, msg=output)


    @plug.repobee_hook
    def clone_task() -> plug.Task:
        return plug.Task(act=act)


    @plug.repobee_hook
    def setup_task() -> plug.Task:
        return plug.Task(act=act)

As you can see, it's rather uncomplicated. The ``act`` function simply finds
files in the repository at ``path``, and returns a
:py:class:`~repobee_plug.Result` with the results. Returning a
:py:class:`~repobee_plug.Result` is optional, but if you don't RepoBee will
not report any results for your plugin. As listing files makes sense both for
student and master repos, we can safely implement both the ``setup_task`` and
``clone_task`` hooks, and return a :py:class:`~repobee_plug.Task` with the
``act`` callback specified. And that's really all there is to to it.

There are some other notable files that you should be familiar with as well.

* ``README.md``: You know what this is.
* ``LICENSE``: This is the license file, which is relevant if you put this in a
  public repository (for example on GitHub). It's an MIT license by default, but
  you can of course change it to whatever you want.
* ``setup.py``: This is the file that allows the plugin to be installed. It will
  work out-of-the-box. If you add any dependencies to your plugin, you must list
  them in the ``required`` attribute in ``setup.py``. See `Packaging Python
  Projects <https://packaging.python.org/tutorials/packaging-projects/>` for
  details.
* ``repobee_exampleplug/__version.py``: This contains the version number for the
  plugin. It defaults to ``0.0.1``. This is only important if you plan to
  distribute your plugin.
* ``tests/`` A directory with unit tests. It starts with a single default test
  that makes sure the plugin can be registered with RepoBee, which is a minimum
  requirement for it actually working.

And that's it for creating a basic plugin.

.. _install local:

Interlude - Installing your plugin
----------------------------------

Since you're here looking how to create your own plugins, I'm guessing you've
already tried using a plugin or two (if not, have a look at the :ref:`plugins`
section). To be able to use the ``exampleplug`` plugin that we just created, it
needs to be installed. That can easily be done like this:

.. code-block:: bash

    # local install
    $ python3 -m pip install --user --upgrade path/to/repobee-exampleplug
    # or from a Git repository
    $ python3 -m pip install --user --upgrade git+https://urltogitrepo.git

.. important::

    Each time you update your plugin, you must install it again!


To check that the plugin was installed correctly and is recognized, we can run
RepoBee with the plugin enabled and request the help section.

.. code-block:: bash

    $ repobee -p exampleplug --help

In the displayed help section, just over the list of positional arguments, you
should see something that looks like this:

.. code-block:: bash

    Loaded plugins: exampleplug-0.0.1, defaults-2.4.0

If you see ``exampleplug`` listed among the plugins, then it was correctly
installed! To try it out, you can simply run the ``clone`` or ``setup`` command
with ``exampleplug`` enabled. It should give you output like this:

.. code-block:: bash

    $ repobee -p exampleplug clone --mn task-1 -s slarse
    [INFO] Cloning into student repos ...
    [INFO] Cloned into https://[...]/slarse-task-1
    [INFO] Executing tasks ...
    [INFO] Processing slarse-task-1
    [INFO] hook results for slarse-task-1

    exampleplug: SUCCESS
    /tmp/tmp_p0v8ha2/slarse-task-1/src
    /tmp/tmp_p0v8ha2/slarse-task-1/README.md
    /tmp/tmp_p0v8ha2/slarse-task-1/.gitignore
    /tmp/tmp_p0v8ha2/slarse-task-1/docs
    /tmp/tmp_p0v8ha2/slarse-task-1/src/README.md
    /tmp/tmp_p0v8ha2/slarse-task-1/docs/README.md

If you've gotten this far, then your plugin is working and you can start
adapting it to your needs. If you need more advanced functionality for your
task, such as the possibility of providing command line options or config
values, then have a look at the advanced task in the next section.

Advanced
--------

You can generate an advanced task plugin with the same cookiecutter template by
selecting "yes" on the ``generate_advanced_task`` option. The advanced task
template does the same thing as the basic one, but it also accepts a command
line option (``--exampleplug-pattern``), which can also be configured in the
config file by adding the ``pattern`` option to the ``[exampleplug]`` section.
Before you proceed with this section, make sure to have a careful look at the
:py:class:`~repobee_plug.Task` data structure. When you've done so, proceed
with generating a plugin like this:

.. code-block:: bash
    :caption: Generating an advanced task plugin

    $ python3 -m cookiecutter gh:repobee/repobee-plugin-cookiecutter
    author []: Simon Larsén
    email []: slarse@slar.se
    github_username []: slarse
    plugin_name []: exampleplug
    short_description []: An example task plugin
    Select generate_basic_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    Select generate_advanced_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]: 2
    $ ls
    repobee-exampleplug

The layout will be *exactly* the same as with the :ref:`basic task` task, but
the ``exampleplug.py`` file will be much more elaborate. It is a bit on the
large side so I won't inline it here, but I can point out the differences.

* The plugin is implemented as a class that extends the
  :py:class:`~repobee_plug.Plugin` class, as described in :ref:`plugin class`
  for non-trivial plugins.
* The ``add_option`` callback is implemented to add a few options to the
  parser.
* The ``handle_args`` callback is also provided to handle the new options added
  by ``add_option``. The reason that ``handle_args`` is a separate callback,
  instead of just passing parsed args to the ``act`` callback, is to allow for
  fail-fast behavior in case of bad arguments. The ``act`` callback is
  typically called fairly late in the execution of RepoBee, but the
  ``handle_args`` callback can be called very early.
* It also implements
  :py:meth:`~repobee_plug._exthooks.CloneHook.config_hook` to access the
  configuration file. There are a few reasons why there is no
  ``handle_config``-ish callback in :py:class:`~repobee_plug.Task`. First,
  config file handling can't depend on the context (e.g. if ``setup`` or
  ``clone`` is called), as the config file is accessed before the CLI arguments
  are parsed. Second, there are other plugins (such as extension commands) that
  also need to be able to access the config file, so it's easier to simply have
  one way of doing it.

.. note::

    If you named your plugin something other than ``exampleplug``, then the
    command line option and config file sections will be named accordingly.

If you install the plugin as specified in the :ref:`install local` section and
run ``repobee -p exampleplug clone -h``, you should see the added command line
option listed in the help section. The plugin can then for example be run like
this to list only files ending with ``md``:


.. code-block:: bash

    $ repobee -p exampleplug clone --mn task-1 -s slarse --exampleplug-pattern '.*md'
    [INFO] Cloning into student repos ...
    [INFO] Cloned into https://[...]/slarse-task-1
    [INFO] Executing tasks ...
    [INFO] Processing slarse-task-1
    [INFO] hook results for slarse-task-1

    exampleplug: SUCCESS
    /tmp/tmp_p0v8ha2/slarse-task-1/README.md
    /tmp/tmp_p0v8ha2/slarse-task-1/src/README.md
    /tmp/tmp_p0v8ha2/slarse-task-1/docs/README.md

That's pretty much it for tasks. Refer to the documentation of the individual
parts for details.

Creating extension command plugins
==================================
An extension command is a top-level command in the RepoBee CLI which seamlessly
integrates with the base tool. Creating an extension command is fairly similar
to creating an advanced task, but it is somewhat easier as an extension
command does not need to integrate into an existing command, making the
definition simpler. For a user, calling an extension command is as simple as
enabling the plugin and running ``repobee <EXT_COMMAND_NAME>``. As an example,
the built-in ``config-wizard`` command is actually implemented as an extension
command. Before we dive into how to create an extension command plugin, let's
first have a look at the core components that make up extension commands.

Extension command components
----------------------------
Extension commands consist of two primary components: the
:py:class:`~repobee_plug.ExtensionCommand` container and the
:py:class:`~repobee_plug.ExtensionParser` parser class.

The ExtensionParser
+++++++++++++++++++
A :py:class:`~repobee_plug.ExtensionParser` is fairly straightforward: it's
simply a thin wrapper around an :py:class:`argparse.ArgumentParser` that's
instantiated without any arguments. It can then be used identically to an
:py:class:`argparse.ArgumentParser`.

.. code-block:: python
    :caption: Example usage of an ExtensionParser

    import repobee_plug as plug

    parser = plug.ExtensionParser()
    parser.add_argument(
        "-n",
        "--name",
        help="Your name.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-a",
        "--age",
        help="Your age.",
        type=int,
    )

The :py:class:`~repobee_plug.ExtensionParser` is then added to an extension
command, which we'll have a look at next.

The ExtensionCommand
++++++++++++++++++++
:py:class:`~repobee_plug.ExtensionCommand` defines an extension command in much
the same way as a :py:class:`~repobee_plug.Task` defines a task. Most of its
properties are self-explanatory, but the ``callback``, ``requires_api`` and
``requires_base_parsers`` deserve a closer look.

First of all, ``requires_base_parsers`` is an interesting feature which allows
an extension command to request parser components from RepoBee's core parser.
The currently available parsers are defined in the
:py:class:`~repobee_plug.BaseParser` enum. As an example, if you provide
``requires_base_parsers=[plug.BaseParser.STUDENTS]``, the
``--students`` and ``--students-file`` options are added to the extension
parser. Not only does this add options to your parser, but they are processed
automatically as well. In the case of the students parser, RepoBee will
automatically check the configuration file for the ``students_file`` option, and
also parse the raw CLI input into a list of :py:class:`~repobee_plug.Team`
tuples for you. In essence, the parsers you can request to have added are parsed
and processed automatically by RepoBee in such a way that your extension command
can provide the same experience as RepoBee's core commands, without having to do
any work. This is only semi-well documented at the moment, but it's easy enough
to simply try passing different base parsers to the ``requires_base_parsers``.

The ``callback`` should be a function that accepts the parsed arguments from the
extension command's parser, as well as an :py:class:`~repobee_plug.API`
instance. Again, if the command requires any base parsers, the arguments from
these will be both parsed and processed. The ``api`` argument is only passed a
meaningful value if ``requires_api=True``, otherwise ``None`` is passed.

Basic
-----
Of course, the `repobee-plugin-cookiecutter template
<https://github.com/repobee/repobee-plugin-cookiecutter>`_ has starter code for
extension commands. There's a basic and an advanced template, and we'll start
with the basic one.


.. code-block:: bash
    :caption: Generating a basic extension command plugin

    $ python3 -m cookiecutter gh:repobee/repobee-plugin-cookiecutter
    author []: Simon Larsén
    email []: slarse@slar.se
    github_username []: slarse
    plugin_name []: exampleplug
    short_description []: An example task plugin
    Select generate_basic_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    Select generate_advanced_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    Select generate_basic_extension_command:
    1 - no
    2 - yes
    Choose from 1, 2 [1]: 2
    Select generate_advanced_extension_command:
    1 - no
    2 - yes
    Choose from 1, 2 [1]:
    $ ls
    repobee-exampleplug

It will again generate the same directory structure as for tasks, but the plugin
will look something like this instead:

.. code-block:: bash
    :caption: exampleplug.py

    import argparse
    import configparser
    from typing import List, Mapping, Optional

    import repobee_plug as plug

    PLUGIN_NAME = "exampleplug"

    def callback(
        args: argparse.Namespace, api: Optional[plug.API]
    ) -> Optional[plug.Result]:
        # do whatever you want to do!
        return plug.Result(
                name=PLUGIN_NAME, status=plug.Status.SUCCESS, msg="Hello, world!"
            )
        }

    @plug.repobee_hook
    def create_extension_command() -> plug.ExtensionCommand:
        """Create an extension command with no arguments.

        Returns:
            The extension command to add to the RepoBee CLI.
        """
        return plug.ExtensionCommand(
            parser=plug.ExtensionParser(), # empty parser
            name="example-command",
            help="An example command.",
            description="An example extension command.",
            callback=callback,
        )

This extension command does nothing, it simply reports some results to RepoBee
with the :py:class:`repobee_plug.Result` data structure. Installing this (see
:ref:`install local`) and enabling it (again with ``-p exampleplug``) will add
the ``example-command`` command to your RepoBee CLI.

.. code-block:: bash

	$ repobee -p exampleplug example-command
	[INFO] hook results for exampleplug

	exampleplug: SUCCESS
	Hello, world!

Not very interesting, but it gives you a base to start on to do very simple
extension commands. To also add command line options, configuration file parsing
and the like, see the advanced extension.


Advanced
--------
To generate the advanced extension command, simply select it when running the
template generation.

.. code-block:: bash
    :caption: Generating an advanced extension command plugin

    $ python3 -m cookiecutter gh:repobee/repobee-plugin-cookiecutter
    author []: Simon Larsén
    email []: slarse@slar.se
    github_username []: slarse
    plugin_name []: exampleplug
    short_description []: An example task plugin
    Select generate_basic_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    Select generate_advanced_task:
    1 - no
    2 - yes
    Choose from 1, 2 (1, 2) [1]:
    Select generate_basic_extension_command:
    1 - no
    2 - yes
    Choose from 1, 2 [1]:
    Select generate_advanced_extension_command:
    1 - no
    2 - yes
    Choose from 1, 2 [1]: 2
    $ ls
    repobee-exampleplug

Again, it will have the exact same directory structure as all the other plugins
that we've generated, and all differences are contained in ``exampleplug.py``.
This extension command adds options, uses the configuration file and has
internal state. It is much too large to include here, but I recommend that you
simply read the source code and try to figure out how it works. Given the time,
I will add more elaborate instructions here, but right now this is as far as I
can take it.
