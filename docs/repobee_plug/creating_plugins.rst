.. _creating plugins:

Creating plugins
****************

Creating plugins for RepoBee is not difficult, and you do not need to be a
seasoned Python developer in order to make something that is genuinely useful.
While it is possible to develop plugins according to all of the best practices
of Python development, you don't need to. In fact, all you need to create your
first plugin is to write a little bit of code in a Python source file. Let's
have a go at extending the RepoBee CLI with the mandatory Hello World example.
Copy the following lines of code into a file called ``hello.py``.

.. code-block:: python
    :caption: hello.py

    import repobee_plug as plug

    class Hello(plug.Plugin, plug.cli.Command):

        def command(self, api):
            print("Hello, world!")

This plugin will add a command called ``hello`` to the command line. As we
haven't specified a category nor action, it will simply be a top-level command.
You can call it like this:

.. code-block:: bash

    $ repobee --plug hello.py hello
    Hello, world!

Of course, this plugin is useless. We will elaborate upon this useless plugin in
this section to illustrate the core concepts of creating plugins for RepoBee.

