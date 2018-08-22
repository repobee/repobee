.. _install:

Install
*******

Requirements
------------
``repomate`` requires Python 3.5+ and a somewhat up-to-date version of ``git``.
Officially supported platforms are ``Ubuntu 17.04+`` and ``OSX``, but
``repomate`` should run fine on any Linux distribution and also on WSL_ on
Windows 10. Please report any issues with operating systems and/or ``git``
versions on the `issue tracker`_.

.. _pypi:

Check your Python version
-------------------------
For ``repomate`` to run, you need to have Python 3.5 or later. On many
operating systems, ``python`` is an alias for Python 2.7, and ``python3`` is an
alias for the latest version of Python 3 that is installed. For this install
guide, ``python3`` is assumed to be a Python version 3.5 or higher. You can
check the version yourself with:

.. code-block:: bash

    $ python3 --version
    # or
    $ python --version

Option 1: Install from PyPi with `pip`
--------------------------------------

The latest release of ``repomate`` is on PyPi, and can thus be installed as usual with ``pip``.
I strongly discourage system-wide ``pip`` installs (e.g. ``sudo pip install <package>``), as this
may land you with incompatible packages in a very short amount of time. A per-user install
can be done like this:

1. Execute ``python3 -m pip install --user repomate`` to install the package.
2. Run ``repomate -h`` to verify that you can find the script.
   - If that doesn't work, the ``repomate`` script can't be found. try
   ``python3 -m repomate -h`` to run ``repomate`` as a module instead.

.. important::

    A ``--user`` install will perform a local install for the current user. Any
    scripts will be installed in a user-local bin directory. If this directory
    is not on your path (which it often is not by default), you will not be
    able to run the ``repomate`` (however, ``python -m repomate`` should still
    work). ``pip`` should issue a warning about this, including the path to the
    local bin directory. To resolve the problem, add the local bin directory to
    your $PATH variable.

.. _clone repo:

Option 2: Clone the repo and the install with `pip`
---------------------------------------------------

If you want the dev version, you will need to clone the repo, as only release versions are uploaded
to PyPi. Unless you are planning to work on this yourself, I suggest going with the release version.

1. Clone the repo with ``git``:
    - ``git clone https://github.com/slarse/repomate``
2. ``cd`` into the project root directory with ``cd repomate``.
3. Install the requirements with ``python3 -m pip install -r requirements.txt``
    - To be able to run the tests, you must install the ``requirements.test.txt`` file.
4. Install locally with ``pip``.
    - ``python3 -m pip install --user .``, this will create a local install for the current user.
    - Or just ``pip install .`` if you use ``virtualenv``.
    - For development, use ``pip install -e .`` in a ``virtualenv``.

.. _WSL: https://docs.microsoft.com/en-us/windows/wsl/install-win10
.. _issue tracker: https://github.com/slarse/repomate/issues
