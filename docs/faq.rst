.. _faq:

Troubleshooting FAQ
*******************

Welcome to the troubleshooting FAQ! If you do not find an answer to your
question, feel free to open an `issue on the issue tracker
<https://github.com/repobee/repobee/issues/new>`_ or reach out via email to
anyone in the `core team <https://repobee.org/pages/contact.html>`_.

There's no ``repobee`` command in my shell
==========================================

The most common cause of this issue is that the ``repobee`` executable is not
on the path, but there could be other explaniations as well. First, try
starting a new shell. You may even need to log out and log back in, depending
on where you appendend to the PATH varible.

If starting a new shell or restarting logging out and back in does not resolve
the issue, check if you have the ``~/.repobee/bin`` directory on your PATH
variable.

.. code-block:: bash

    $ echo $PATH | grep -o "$HOME/.repobee/bin"

If you get no output, then the directory is not on your PATH. Before adding the
bin directory to your path, you can check that the executable is actually
present on your system.

.. code-block:: bash
    :caption: Expected content in RepoBee's bin directory

    $ ls -l ~/.repobee/bin
    lrwxrwxrwx 1 slarse slarse 37 Sep  2 14:37 repobee -> /home/slarse/.repobee/env/bin/repobee

If your output looks something like this, then you've got RepoBee installed.
If it does *not* look like this (e.g. the symlink is dangling or the directory
dous not exist), then you should try executing the installer again. Once you
see the directory and a valid symlink, try directly executing the executable
with a qualified path.

.. code-block:: bash
    :caption: Executing RepoBee with a qualified path

    $ ~/.repobee/bin/repobee -h
    # help output should pop up here

If that works, all you need to do is to add the bin directory to your PATH.
Where you should do that depends on what shell you use. For example, for `bash
you should typically put environment variables in ~/.profile
<https://help.ubuntu.com/community/EnvironmentVariables#Session-wide_environment_variables>`_,
for `zsh they typically go in ~/.zshenv
<http://zsh.sourceforge.net/Intro/intro_3.html>`_, and for `fish they go in
~/.config/fish/config/fish <https://fishshell.com/docs/2.2/faq.html>`_.

.. code-block:: bash
    :caption: Example PATH configuration

    # for bash, add this to your ~/.profile
    export PATH="$PATH:$HOME/.repobee/bin"

    # for zsh, add this to your ~/.zshenv
    export PATH="$PATH:$HOME/.repobee/bin"

    # for fish, add this to your ~/.config/fish/config.fish
    set -x PATH "$PATH:$HOME/.repobee/bin"

.. important::

    With bash, the ``.profile`` file can be overridden by the
    ``~/.bash_profile`` file.

Error message `bad interpreter: No such file or directory"`
===========================================================

This is typically caused by the system wide Python executable being upgraded or
otherwise changed after installing RepoBee. To fix this, remove the
``~/.repobee`` directory and then execute the installer again (see
:ref:`install`).

RepoBee crashes
===============

Very often, RepoBee crashing is due to a faulty plugin, or bad configuration of
a plugin. When this is the case, use the ``--no-plugins`` option for the
preparser to disable plugins.

.. note::

    ``--no-plugins`` is a *preparser* option, meaning that it should be passed
    directly after typing ``repobee``. For example, to run ``repobee plugin
    uninstall`` without plugins, run like so:

    .. code-block::
        :caption: Uninstalling plugins with all installed plugins disabled

        $ repobee --no-plugins plugin uninstall

All of the troubleshooting steps in this section will use ``--no-plugins``.

An option in the config file is causing problems
------------------------------------------------

If you have misconfigured a plugin, or have an outdated option, you may
sometimes need to  manually remove the option from the config file.
Run the following to find out where the config file is located.

.. code-block::
    :caption: Finding out where the config file is located

    $ repobee --no-plugins config show

The location of the config file is printed at the very top of the message.
Edit it with any text editor and remove the option that causes issues.

A plugin has broken down
------------------------

If a plugin isn't working (even after removing faulty options), try to upgrade
both the plugin and RepoBee itself.

.. code-block::
    :caption: Upgrade RepoBee and install the plugin again

    $ repobee --no-plugins manage upgrade
    $ repobee --no-plugins plugin install

Nothing works, it's still broken
--------------------------------

If none of that works, the simplest thing is to reinstall RepoBee. This does
*not* affect your settings in the config file, it only affects installed
plugins, and so is low-risk to do. To do it, just remove the directory at
``~/.repobee`` and install RepoBee again, as described in :ref:`install`.
