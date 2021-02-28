.. _install:

Install
*******

Requirements
------------

RepoBee requires Python 3.6+ and a somewhat up-to-date version of Git (2.0+ to
be on the safe side). Officially supported operating systems are Ubuntu 17.04+
and macOS, but RepoBee runs fine on most Linux distributions, and also on WSL_
on Windows 10. Please report any issues with operating systems and/or Git
versions on the `issue tracker`_.

Installing RepoBee
------------------

RepoBee's install script will guide you through the installation process. It
will check that you have all necessary software and provide you with links to
relevant resources if you do not. To run the script, you need either ``bash``
or ``zsh``, but it's possible to run RepoBee from virtually any shell.

Below you'll see the command to execute to get and execute the install script.
Note that it requires ``curl`` to be installed.

.. code-block:: bash

    # for bash
    $ bash <(curl -s https://repobee.org/install.sh)

    # for zsh
    $ zsh <(curl -s https://repobee.org/install.sh)


.. _WSL: https://docs.microsoft.com/en-us/windows/wsl/install-win10
.. _issue tracker: https://github.com/repobee/repobee/issues

.. _completion:

Tab completion
--------------

RepoBee supports tab completion (aka auto completion, shell completion, etc) for
``bash`` and ``zsh``, but it must be enabled separately after installing RepoBee
by executing a script found in the install directory. The procedure differs
slightly between the two shells.

.. note::

    This guide assumes you've installed RepoBee at ``~/.repobee``. If you don't
    make an active choice saying otherwise, that's where RepoBee is installed.
    The install script also explicitly tells you where it's installing RepoBee.
    If you've chosen to install RepoBee in any other directory, then you need to
    make the proper path substitutions in the below instructions.

bash
++++

For ``bash``, simply add the following line to your ``~/.bashrc`` file.

.. code-block:: bash

    source ~/.repobee/completion/bash_completion.sh

zsh
+++

For ``zsh``, you must make sure to enable bash completion, and then source the
completion script. The entire thing looks like so.

.. code-block:: bash

    autoload -Uz compinit
    compinit
    autoload -Uz bashcompinit
    bashcompinit
    source ~/.repobee/completion/bash_completion.sh

.. important::

    You should *not* have multiple occurences of ``compinit`` and
    ``bashcompinit`` in your .zshrc, they should be loaded and executed only
    once. If you already have them in there, just make sure to source the
    RepoBee bash completion script after compinit and bashcompinit have been
    called.
