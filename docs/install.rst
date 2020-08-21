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
