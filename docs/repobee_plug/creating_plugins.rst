.. _creating plugins:

Creating plugins
****************

We've put a lot of effort into making the creation of plugins as easy as
possible, and you do not need to be a seasoned Python developer in order to
make something that is genuinely useful.  While it is possible to develop
plugins according to all of the best practices of Python development, you don't
need to. In fact, all you need to create your first plugin is to write a little
bit of code in a Python source file. Let's have a go at extending the RepoBee
CLI with the mandatory Hello World example.  Copy the following lines of code
into a file called ``hello.py``.

.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug

    class HelloWorld(plug.Plugin, plug.cli.Command):

        def command(self, api):
            plug.echo("Hello, world!")

This plugin will add a command called ``helloworld`` to the command line. As we
haven't specified a category nor action, it will simply be a top-level command.
You can call it like this:

.. code-block:: bash

    $ repobee --plug hello.py helloworld
    Hello, world!

Of course, this plugin is useless. We will elaborate upon this useless plugin
in this section to illustrate the core concepts of creating plugins for
RepoBee. It will in the end still be quite useless, but it'll be a bit more
fun.

.. note::

    By default, the command line action will be given the name of the command
    class, but in all lowercase. In this case, ``HelloWorld`` became
    ``helloworld``.

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

        def command(self, api):
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

		def command(self, api):
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

.. code-block:: raw

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

.. code-block:: raw

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

        def command(self, api):
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

.. code-block:: raw

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

        def command(self, api):
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

.. code-block:: raw

    $ repobee -p hello.py config wizard
    Select a section to configure:
     repobee
    ●hello

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
