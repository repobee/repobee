gits_pet
*******************************************************

`Docs`_

.. image:: https://travis-ci.com/slarse/gits_pet.svg?token=1VKcbDz66bMbTdt1ebsN&branch=master
    :target: https://travis-ci.com/slarse/gits_pet
    :alt: Build Status
.. image:: https://codecov.io/gh/slarse/gits_pet/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/slarse/gits_pet
    :alt: Code Coverage
.. image:: https://readthedocs.org/projects/gits_pet/badge/?version=latest
    :target: http://gits_pet.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://badge.fury.io/py/gits_pet.svg
    :target: https://badge.fury.io/py/gits_pet
    :alt: PyPi Version
.. image:: https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg
    :alt: Supported Python Versions

.. contents::

Overview
========
A CLI tool for administrating large amounts of GitHub repositories, geared towards teachers.

Requirements
============
To be added ...

Install
=======

Option 1: Install from PyPi with ``pip``
----------------------------------------

.. important:: Not yet available on PyPi! This section will be needed at a later stage.


The latest release of ``gits_pet`` is on PyPi, and can thus be installed as usual with ``pip``.
I strongly discourage system-wide ``pip`` installs (i.e. ``sudo pip install <package>``), as this
may land you with incompatible packages in a very short amount of time. A per-user install
can be done like this:

1. Execute ``pip install --user gits_pet`` to install the package.
2. Further steps to be added ...


Option 2: Clone the repo and the install with ``pip``
-----------------------------------------------------
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
5. Further steps to be added ...

Running gits_pet
================
To be added ...
   
License
=======
This software is licensed under the MIT License. See the `license file`_ file for specifics.

Contributing
============
To be added ...

.. _license file: LICENSE
.. _sample configuration: config.cnf
.. _requirements: requirements.txt
.. _test requirements: requirements.test.txt
.. _Docs: https://gits_pet.readthedocs.io/en/latest/
