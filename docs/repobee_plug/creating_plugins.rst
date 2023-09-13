.. _creating plugins:

Creating plugins
****************

We've put a lot of effort into making the creation of plugins as easy as
possible, and you do not need to be a seasoned Python developer in order to
make something that is genuinely useful. While it is possible to develop
plugins according to all of the best practices of Python development, you don't
need to. In fact, all you need to create your first plugin is to write a little
bit of code in a Python source file. Let's have a go at extending the RepoBee
CLI with the mandatory Hello World example. Copy the following lines of code
into a file called ``hello.py``.

.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug

    class HelloWorld(plug.Plugin, plug.cli.Command):

        def command(self):
            plug.echo("Hello, world!")

This plugin will add a command called ``helloworld`` to the command line. As we
haven't specified a category nor action, it will simply be a top-level command.
As the plugin is contained in a single file, we call it a *single-file plugin*.
You can activate the plugin temporarily with ``-p /path/to/hello.py`` in order
to call the command defined in it.

.. code-block:: bash

    $ repobee -p hello.py helloworld
    Hello, world!

Of course, this plugin is useless. We will elaborate upon this useless plugin
in this section to illustrate the core concepts of creating plugins for
RepoBee. It will in the end still be quite useless, but it'll be a bit more
fun.

.. note::

    By default, the command line action will be given the name of the command
    class, but in all lowercase. In this case, ``HelloWorld`` became
    ``helloworld``.

.. _plugin commands:

Commands
========

What we saw in the previous section was a plugin *command*. This is a
standalone command that integrates seamlessly with the RepoBee interface.
There are many ways in which a plugin command can be customized, such as by
adding command line arguments and integrating deeper with RepoBee's
functionality.

There are other forms of plugins you can create for RepoBee, but we'll start
with plugin commands as they are the easiest to grasp, being standalone pieces
of code.

Adding command settings
-----------------------

All commands in RepoBee's core are on the form ``repobee <category> <action>``,
but the hello world command we created in the beginning of this section was run
simply with ``repobee hello``. To better mesh with the rest of RepoBee, we can
add a category to our plugin command. This can either be one of RepoBee's
existing categories, or a brand new one that we create just for this plugin.
Let's start with adding it to RepoBee's ``config`` category. We do that by
adding the ``__settings__`` attribute. While we're at it, let's also customize
help text and the name of the action itself.

.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug

    class HelloWorld(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            category=plug.cli.CoreCommand.config,
            action="hello",
            help="say hello to the world",
            description="Say hello to the world. And in style.",
        )

        def command(self):
            plug.echo("Hello, world!")

.. code-block:: bash

    $ repobee -p hello.py config -h
    usage: repobee config [-h] {show,verify,hello,wizard} ...

    Configure RepoBee.

    positional arguments:
      {show,verify,hello,wizard}
        show                show the configuration file
        verify              verify core settings
        hello               say hello to the world
        wizard              interactive configuration wizard to set up the config file

    $ repobee -p hello.py config hello -h
    usage: repobee config hello [-h] [--tb]

    Say hello to the world. And in style.

    optional arguments:
      -h, --help         show this help message and exit
      --tb, --traceback  show the full traceback of critical exceptions

    $ repobee -p hello.py config hello
    Hello, world!

Note where the ``help`` text and the ``description`` texts go. It's good
practice in RepoBee to have the ``help`` text to be in all lower case, without
punctuation. The ``description`` can be however long you'd like.

Another thing we can do is to create a new category for the plugin command.
That looks something like this.

.. code-block:: python
    :caption: hello.py

	import repobee_plug as plug

	hello_category = plug.cli.category(
		name="greetings",
		action_names=["hello"],
		help="greetings and good tidings",
		description="Use social skills to produce excellent greetings.",
	)


	class HelloWorld(plug.Plugin, plug.cli.Command):
		__settings__ = plug.cli.command_settings(
			action=hello_category.hello,
			help="say hello to the world",
			description="Say hello to the world. And in style.",
		)

		def command(self):
			plug.echo("Hello, world!")

The command is now accessible from ``repobee -p hello.py greetings
hello``. Note in the ``command_settings`` that only the action is
specified. When you specify the aciton as an attribute of a category, the
category itself is implied by the action.

And that's more or less it for basic command configuration. Let's move on to
command line arguments.

Adding command line arguments
-----------------------------

RepoBee currently provides three basic forms of command line arguments:
:py:func:`~repobee_plug.cli.option`, :py:func:`~repobee_plug.cli.positional`
and :py:func:`~repobee_plug.cli.flag`. We will cover them all in turn.

Options
+++++++

You can add command line options with the :py:func:`repobee_plug.cli.option`
function. An option is a key-value pair, typically used like so:

.. code-block:: bash

    --option-name value

They are the most common way to provide command line arguments in RepoBee.
Options can be specified in any order on the command line, and may or may not
be required.

Positionals
+++++++++++

You can add command line possitionals with the
:py:func:`repobee_plug.cli.positional` function. Positionals are always
required arguments, and appears on the command in the order they are declared.

Flags
+++++

A flag is a special case of an option that can be added with the
:py:func:`repobee_plug.cli.flag` function. Usage looks like this.

.. code-block:: bash

    --flag-name

Typically, specifying the flag sets its corresponding value to ``True``, and
leaving it unspecified causes it to default to ``False``. One can however
reverse that, or let the flag specify entirely arbitrary values.

Example usage
+++++++++++++

Let's use all types of command line arguments in our fantastic ``hello.py``
plugin.

.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug
    import datetime

    hello_category = plug.cli.category(
        name="greetings",
        action_names=["hello"],
        help="greetings and good tidings",
        description="Use social skills to produce excellent greetings.",
    )


    class Hello(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            action=hello_category.hello,
            help="say hello to the world",
            description="Say hello to the world. And in style.",
        )

        world = plug.cli.positional(help="synonym to use instead of 'world'")

        date = plug.cli.option(
            help="the current date on the form 'yy-mm-dd'",
            converter=datetime.date.fromisoformat,
            default=datetime.date.today(),
        )

        is_fantastic = plug.cli.flag(help="set if you think this is fantastic")

        def command(self):
            world_state = "fantastic" if self.is_fantastic else "awful"
            plug.echo(f"Hello, {world_state} {self.world}, at {self.date}")

Usage then looks like so:

.. code-block:: bash

    $ repobee -p hello.py greetings hello --help
    usage: repobee greetings hello [-h] [--tb] [--date DATE] [--is-fantastic] world

    Say hello to the world. And in style.

    positional arguments:
      world              synonym to use instead of 'world'

    optional arguments:
      -h, --help         show this help message and exit
      --date DATE        the current date on the form 'yy-mm-dd'
      --is-fantastic     set if you think this is fantastic
      --tb, --traceback  show the full traceback of critical exceptions

    $ repobee -p hello.py greetings hello mundo --is-fantastic
    Hello, fantastic mundo, at 2020-08-17

There are a few things to note here. First of all, the command line arguments
are simply added as attributes to the class, and are then accessed via
``self``. The ``help`` attribute can always be added, and is displayed in the
help section when invoking the command with ``-h|--help``. The default type of
a CLI argument is ``str``, but it can be converted to any type using a
``converter`` function that takes a string and returns... some other type. Note
that the converter also doubles as a validator. For example, where I to enter
a date on the wrong format, it would look something like this:

.. code-block:: bash

    $ repobee -p hello.py greetings hello mundo --is-fantastic --date 2020-08
    usage: repobee greetings hello [-h] [--tb] [--date DATE] [--is-fantastic] world
    repobee greetings hello: error: argument --date: invalid fromisoformat value: '2020-08'

Also note that we provided a default value to ``date``. Had we not done so, not
specifying ``--date`` would result in it being ``None``. If you want to make sure
that an option is specified, you must either add ``default=<SOMETHING>`` or
``required=True``. The latter forces the user to specify the option on the
command line.

Configurable options
++++++++++++++++++++

The :py:func:`~repobee_plug.cli.option` function has one really neat piece of
magic: the ``configurable`` argument. If you set ``configurable=True``, RepoBee
will look for the option in the configuration file. Let's make the ``date``
option configurable.


.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug
    import datetime

    hello_category = plug.cli.category(
        name="greetings",
        action_names=["hello"],
        help="greetings and good tidings",
        description="Use social skills to produce excellent greetings.",
    )


    class Hello(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            action=hello_category.hello,
            help="say hello to the world",
            description="Say hello to the world. And in style.",
        )

        world = plug.cli.positional(help="synonym to use instead of 'world'")

        date = plug.cli.option(
            help="the current date on the form 'yy-mm-dd'",
            converter=datetime.date.fromisoformat,
            default=datetime.date.today(),
            configurable=True,
        )

        is_fantastic = plug.cli.flag(help="set if you think this is fantastic")

        def command(self):
            world_state = "fantastic" if self.is_fantastic else "awful"
            plug.echo(f"Hello, {world_state} {self.world}, at {self.date}")

By default, the configuration file section will be the same as the *plugin
name*. In the case of this single file plugin, the name is the name of the
file, without the ``.py`` file extension. You can change this behavior by
explicitly specifying the ``config_section_name`` argument in the command
settings.

Any way you do it, we can configure the plugin with the config wizard. Note
that **the plugin must be active** in order to be configurable, so don't forget
``-p hello.py``. Then, simply select the correct section (``hello``) and
configure the value.

.. code-block:: bash

    $ repobee -p hello.py config wizard
    Select a section to configure:
     repobee
    *hello

    Configuring section: hello
    Type config values for the options when prompted.
    Press ENTER without inputing a value to pick existing default.

    Current defaults are shown in brackets [].

    Enter default for 'date': [] 1970-01-01
    Configuration file written to /home/slarse/.config/repobee/config.ini

If unspecified on the command line, ``date`` will now default to
``1970-01-01``.

There are two things to be aware of with configured values.

1. A configured value *overrides* any default value set in the ``option``
   function.
2. If the option is required *and* configurable, then configuring the value in
   the config file makes the option **not** required.

And that's more or less all there is to it for basic command plugins. See the
:py:mod:`repobee_plug.cli` reference for a complete documentation of the ``cli``
package.

Making use of the platform API
------------------------------

RepoBee provides an abstraction layer against the hosting platform (currently
GitHub or GitLab) in the form of the :py:class:`~repobee_plug.PlatformAPI`.
A plugin command can make use of it by adding an ``api`` argument to the
``command`` function. Here is a simple example of a plugin command that
creates a single repository for a given team.


.. code-block:: python
    :caption: single.py

    class CreateSingle(plug.Plugin, plug.cli.Command):
        __settings__ = plug.cli.command_settings(
            category=plug.cli.CoreCommand.repos, action="create-single"
        )
        team_name = plug.cli.option()
        repo_name = plug.cli.option()

        def command(self, api: plug.PlatformAPI):
            team = api.get_teams(team_names=[self.team_name])[0]

            try:
                repo = api.create_repo(
                    self.repo_name,
                    description=description,
                    private=private,
                    team=team,
                )
                plug.echo(f"Created {repo.name} for {team.name}")
            except plug.PlatformError:
                # this typically happens if the repo already exists
                plug.log.error(f"failed to create {self.team_name}/{self.repo_name}")

.. code-block:: bash

    $ repobee -p single.py repos create-single --team-name slarse --repo-name epic-repo
    Created epic-repo for slarse
    $ repobee -p single.py repos create-single --team-name slarse --repo-name epic-repo
    [ERROR] failed to create slarse/epic-repo

For a full listing of what can be done with the platform API, refer to the
documentation for :py:class:`repobee_plug.PlatformAPI`.

Hooks and command extensions
============================

Throughout RepoBee, there are various *hooks* that a plugin can implement, and
thereby alter or extend the way RepoBee's core functionality operates. There
are two fundamental types of hooks.

* *Core hooks*: These hooks alter RepoBee's core functionality in some way.
  They always have a default implementation in RepoBee's core. You can find all
  available core hooks documented in :py:mod:`repobee_plug._corehooks`.
* *Extension hooks*: These hooks extend RepoBee's core functions in some way.
  They do not have default implementations. You can find all extension hooks
  documented in :py:mod:`repobee_plug._exthooks`.

In this section, we'll have a look at how to implement hooks, and how to extend
RepoBee's existing commands with more command line arguments.

Implementing hooks
------------------

To implement a hook, first find one to implement. For example, we could
implement the ``post_clone`` extension hook, which kicks in after student
repositories have been cloned, like so:


.. code-block:: python
    :caption: ext.py

    import repobee_plug as plug

    @plug.repobee_hook
    def post_clone(repo: plug.StudentRepo, api: plug.PlatformAPI):
        plug.echo(f"Hello, {repo.name}")

The only thing this plugin does is to print the names of repositories to
stdout. Not very useful, and it will look pretty weird on stdout as well due to
the proliferation of progress bars, but it's easy enough to wrap your head
around.

As the ``post_clone`` hook is executed after student repos have been cloned,
the way we see this hook in action is if we run the ``repos clone`` command
with the plugin activated.

.. code-block:: bash
    :caption: Example of how to execute a post_clone plugin

    $ repobee -p ext.py repos clone ...

We can implement the same plugin with the :py:class:`repobee_plug.Plugin`
class, which turns all of the functions inside of it into hooks.

.. code-block:: python
    :caption: ext.py

    import repobee_plug as plug

    class Ext(plug.Plugin):
        def post_clone(self, repo: plug.StudentRepo, api: plug.PlatformAPI):
            plug.echo(f"Hello, {repo.name}")

Note how the ``post_clone`` implementation now does not need the
``@plug.repobee_hook`` decorator. Also note that, as it's now a method, the
``self`` argument must be added. This plugin works identically to the previous
one.

With the basics if implementing hooks out of the way, let's move into something
a bit more interesting: command extensions.

.. _command_extensions:

Command extensions
------------------

A *command extension* is a plugin that extends an existing RepoBee command with
additional CLI arguments, or that otherwise makes use of the CLI arguments
passed to RepoBee.

Let's create a real-ish plugin for this one. Assume that you're teaching a
course in which each student repository contains a ``ci.yml`` file that
configures some form of continuous integration you've got set up for the
students. You want to check that none of the students have accidentally
tampered with this file. Let's also assume that we want to be able to
reuse the plugin for other courses, with other ``ci.yml`` files, and so
we want to pass it as an argument to the CLI. We could then do something like
this:

.. code-block:: python
    :caption: cicheck.py

    import pathlib
    import typing as ty

    import repobee_plug as plug


    class CiCheck(plug.Plugin, plug.cli.CommandExtension):
        __settings__ = plug.cli.command_extension_settings(
            actions=[plug.cli.CoreCommand.repos.clone]
        )

        cicheck_reference_yml = plug.cli.option(
            help="path to the reference ci.yml file",
            converter=pathlib.Path,
            required=True,
        )

        def post_clone(
            self, repo: plug.StudentRepo, api: plug.PlatformAPI
        ) -> ty.Optional[plug.Result]:
            ci_yml_path = repo.path / "ci.yml"

            if not ci_yml_path.is_file():
                return plug.Result(
                    name=repo.name,
                    status=plug.Status.ERROR,
                    msg="ci.yml is missing",
                )

            reference_content = self.cicheck_reference_yml.read_text("utf8")
            actual_content = ci_yml_path.read_text("utf8")
            matches = reference_content == actual_content

            msg = (
                "ci.yml matches reference"
                if matches
                else "ci.yml does not match reference"
            )
            status = plug.Status.SUCCESS if matches else plug.Status.WARNING

            return plug.Result(name=repo.name, status=status, msg=msg)

There are a few important things to note here. First of all, a command
extension *must* have a ``__settings__`` attribute, which should be
instantiated with the :py:func:`~repobee_plug.cli.command_extension_settings`
function. You must also supply this with a list of command line actions to
attach the extension command to. In this case, we are only interested in the
``repos clone`` command, so that's the only action we specify.

Also note that ``post_clone`` may optionally return a
:py:class:`repobee_plug.Result`. This data type is used by RepoBee to report
results to the CLI, and also to the hook results file. The ``name`` is used as
a key to identify what the result belongs to (in this case the repo name), and
the rest of the arguments should be self-explanatory.

Another important aspect is that we add the command line option just like we
would for the regular plugin commands discussed in :ref:`plugin commands`,
with one exception: **the argument name is prefixed with the name of the
plugin**. This is to avoid name collisions with RepoBee's core arguments, or
any other plugins. This is not enforced, but you should always strive to do it.

The usage of this command would then look something like the following.

.. code-block:: bash

    $ repobee -p cicheck.py repos clone --cicheck-reference-yml /path/to/ci.yml [OTHER ARGUMENTS]


.. _packaging_plugins:

Packaging plugins
=================

Single-file plugins are great for experimentation, but they're not very
maintainable in the long run. When plugins grow large, it becomes very
inconvenient to keep them in a single file, and testing becomes a pain. In
order to make a plugin more maintainable, it is possible to create a proper
Python package. This may sound daunting if it's something you've never done
before, but we provide a template to get started from, and so it should not be
too much of a challenge. In this section, we'll walk through how to get
started.

Installing ``cookiecutter``
---------------------------

To use the template, you must have the ``cookiecutter`` Python package
installed. The easiest way to get it is to perform a *user* install.

.. code-block:: bash

    $ python3 -m pip install --user cookiecutter
    # check that it was installed correctly
    $ python3 -m cookiecutter --version

See the `cookiecutter GitHub page for more details
<https://github.com/cookiecutter/cookiecutter>`_.

The ``repobee-plugin-cookiecutter`` template
--------------------------------------------

To use the template, simply execute the following command and answer the
prompts, of course replacing them with the details that are relevant for
you.

.. code-block:: bash

    $ python3 -m cookiecutter gh:repobee/repobee-plugin-cookiecutter
    author []: Repo Bee
    email []: repobee@repobee.org
    plugin_name []: example
    short_description []: An example plugin

With the details entered above, a plugin package will be created in the
directory ``repobee-example``. Its directory structure looks like this.

.. code-block:: bash

  repobee-example
    ├── LICENSE
    ├── README.md
    ├── repobee_example
    │   ├── example.py
    │   ├── __init__.py
    │   └── __version.py
    ├── setup.py
    └── tests
        └── test_example.py

Note the following details:


* A plugin with the *name* ``example`` belongs in a directory called
  ``repobee-example``

    - In the before time, long ago, all RepoBee plugins were distributed on
      PyPi, and this would then have been the name of the package

* There is a file called ``setup.py``

    - This is a barebones rendition of a setup file that makes this an
      installable Python package
    - There is a variable in ``setup.py`` called ``required``. Add dependencies
      to this if you require additional Python packages, and they will be
      installed along with your plugin.
    - See the `Python Packaging Guide
      <https://packaging.python.org/tutorials/packaging-projects/>`_ for more
      details

* The directory with the source code is called ``repobee_example``

    - This is the name of the actual Python package, and it's very important
      that the package is called precisely ``repobee_<plugin_name>``, or
      RepoBee will not find it

* There is a module called ``example.py`` in ``repobee_example``

    - This is the *primary plugin module*
    - It must exist, and it must be called ``<plugin_name>.py``

* The ``tests`` directory comes pre-stocked with a rudimentary test setup for
  `pytest <https://docs.pytest.org/en/latest/>`_

For examples of existing plugins that adhere to these conventions, see for
example `repobee-junit4 <https://github.com/repobee/repobee-junit4>`_ and
`repobee-feedback <https://github.com/repobee/repobee-feedback>`_ Now, let's
talk a bit more about the primary plugin module.

The primary plugin module
-------------------------

The primary plugin module is the only module in a plugin package that RepoBee
actually attempts to load. Therefore, any ``plug.Plugin`` class or
``plug.repobee_hook`` function that you want RepoBee to find, must be found in
this module. This does *not* mean that they must all be defined in the primary
plugin module; it's sufficient that they are imported into it.

The primary plugin module is essentially the same as a single-file plugin,
except that it's packaged such that it can import other modules in the same
package. It can also take advantage of additional dependencies defined in
``setup.py``. Of course, all of the concepts discussed in relation to
single-file plugins apply to packaged plugins, with one important exception: a
packaged plugin must be installed.

Installing a plugin package
---------------------------

Currently, RepoBee only supports installing unofficial plugin packages if they
are local on disk. Assuming your plugin is located at
``/path/to/repobee-example``, you can install it like so.

.. code-block:: bash

    $ repobee plugin install --local /path/to/repobee-example

You can then use it as usual with a plugin, either by activating it
persistently or temporarily. See :ref:`activate_plugins` for details on plugin
activation.

The example plugin generated by the template contains an example "Hello world"
command, so after installing it, you should be able to execute the following
command.

.. code-block:: bash

    $ repobee -p example helloworld

And those are all of the basics of packaging plugins!

Optional: Developing in a virtual environment
---------------------------------------------

Now that you've got everything setup, it's time for one last thing if you want
to do get serious with developing and maintaining your plugin. That thing is a
*virtual environment*, which allows you to install Python dependencies for your
project in an isolated environment. Installing Python packages with a system or
user install should be avoided if at all possible, as you quickly end up in the
dreaded *package hell*. Creating a virtual environment is very easy, as there is
a module for doing so that ships with Python, called ``venv``. In the root
directory of your project (so in this case, in ``repobee-example``), execute the
following.

.. code-block:: bash

    $ python3 -m venv env


.. note::

    On some Linux distributions, ``venv`` is separate from ``python``. For
    example, on Debian you must install it with ``apt install python3-venv``.

This creates a directory called ``env`` in your current working directory,
containing the virtual environment. You can then enter and exit the virtual
environment like so.

.. code-block:: bash

    # activate the virtual environment
    $ source env/bin/activate
    # install the project with an editable install and test requirements
    (env) $ pip install -e .[TEST]
    # run the tests
    (env) $ pytest tests/
    ========================= test session starts =========================
    platform linux -- Python 3.8.6, pytest-6.1.2, py-1.9.0, pluggy-0.13.1
    rootdir: /home/slarse/Documents/github/repobee/repobee-example
    plugins: repobee-3.3.0
    collected 1 item

    tests/test_example.py .                                         [100%]

    ========================== 1 passed in 0.01s ==========================
    # exit the virtual environment
    $ deactivate

When you do development on the project, make sure to enter the virtual
environment first. You don't need to install the local project each time you
enter, but make sure to do so if you 1) add new dependencies in ``setup.py``, or
2) change the version number in ``__version.py``.

.. hint::

    Installing the local directory with ``.[TEST]`` may seem cryptic, but it's
    quite simple. The ``.`` simply means "this directory", and the ``[TEST]``
    means "also install the requirements listed in ``extras_require`` with key
    ``TEST`` in the ``setup.py`` file.

And that's just about what you need to know to do some rudimentary Python
development. For a more in-depth tutorial on using virtual environments,
`see this great article on RealPython
<https://realpython.com/python-virtual-environments-a-primer/>`_.
