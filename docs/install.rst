.. _install:

Install
*******

Requirements
------------
``gits_pet`` requires Python 3.5+ and a somewhat up-to-date version of ``git``.
Officially supported platforms are ``Ubuntu 17.04+`` and ``OSX``, but
``gits_pet`` should run fine on any Linux distribution and also on WSL_ on
Windows 10.  Please report any issues with operating systems and/or ``git``
versions on the issue tracker.

.. _pypi:

Option 1: Install from PyPi with `pip`
--------------------------------------

.. important::

    Not yet available on PyPi, go with `clone repo`_ instead!

The latest release of ``gits_pet`` is on PyPi, and can thus be installed as usual with ``pip``.
I strongly discourage system-wide ``pip`` installs (i.e. ``sudo pip install <package>``), as this
may land you with incompatible packages in a very short amount of time. A per-user install
can be done like this:

1. Execute ``pip install --user gits_pet`` to install the package.
2. Further steps to be added ...

.. _clone repo:

Option 2: Clone the repo and the install with `pip`
---------------------------------------------------

If you want the dev version, you will need to clone the repo, as only release versions are uploaded
to PyPi. Unless you are planning to work on this yourself, I suggest going with the release version.

1. Clone the repo with ``git``:
    - ``git clone https://github.com/slarse/gits_pet``
2. ``cd`` into the project root directory with ``cd gits_pet``.
3. Install the requirements with ``pip install -r requirements.txt``
    - To be able to run the tests, you must install the ``requirements.test.txt`` file.
4. Install locally with ``pip``.
    - ``pip install --user .``, this will create a local install for the current user.
    - Or just ``pip install .`` if you use ``virtualenv``.
    - For development, use ``pip install -e .`` in a ``virtualenv``.

.. _WSL: https://docs.microsoft.com/en-us/windows/wsl/install-win10
