.. _contributing:

Contributing to RepoBee
***********************
This article contains technical information on how to contribute to RepoBee. If
you haven't alredy, first read the information in the
`CONTRIBUTING.md <https://github.com/repobee/repobee/blob/master/CONTRIBUTING.md>`_
in the repo, which details how to submit a proposal. If you've done that, this
article will tell you more about technical details.


Setting up a Development Environment
====================================

Basic Environment to Run Unit Tests
-----------------------------------
The most rudimentary development environment is easy to set up. There are three
tasks to accomplish:

* `Fork the repository <https://help.github.com/en/articles/fork-a-repo>` and
  clone your fork.
* Setup a Python virtual environment and install the project with test
  dependencies.
* Install the pre-commit hooks

So, first `fork the repository
<https://help.github.com/en/articles/fork-a-repo>` and clone your fork down to
disk.

.. code-block:: bash

   # substitute USER for your username
   $ git clone git@github.com:USER/repobee.git

Then, you need to set up a virtual environment in the newly cloned repository.
I'm using ``pipenv`` here, but you can use something else if you have other
preferences.

.. code-block:: bash

   # install pipenv for the local user
   $ python3 -m pip install --user pipenv
   # move into the repobee directory and install the repobee package with pipenv
   $ cd repobee
   $ python3 -m pipenv install -e .[TEST]

The last thing takes a while, so just be patient. When it's done, you can verify
that everything was installed correctly by running the tests in the virtual
environment.

.. code-block:: bash

   $ python3 -m pipenv run pytest tests/unit_tests

Everything should pass. Now, you can run any command in the virtualenv by
prepending it with ``python3 -m pipenv run``. However, it is often more
convenient to "enter" the virtual environment with ``python3 -m pipenv shell``,
and type ``exit`` to exit it. Then, you can just type in your Python commands
as usual, and the virtual environment's Python program will be used.

.. _pre-commit hooks:

Pre-commit Hooks
++++++++++++++++
Finally, you should also install the pre-commit hooks that come with RepoBee.
They make some rudimentary checks to primarily code style before a commit can be
recorded. They require the ``pre-commit`` package. I recommend installing this
*outside* of the virtual environment so that hooks can run even if you are not
in the virtual environment shell. In the root of the project, run:

.. code-block:: bash

   $ python3 -m pip install --user pre-commit
   $ python3 -m pre-commit install

And that's it, the environment is all set up!

Full Environment to Run Integration/System Tests
------------------------------------------------
To also run the integration/system tests located in ``tests/integration_tests``,
you need to have Docker and Docker Compose installed, and the Docker daemon
(service) must be running. Installing these utilities will vary by distribution,
here are a few examples:

.. code-block:: bash

   # Arch Linux
   $ sudo pacman -Sy docker docker-compose
   # Ubuntu
   $ sudo apt install docker docker-compose
   # CentOS/REHL
   $ sudo yum -y install epel-release # docker-compose is in the EPEL repos
   $ sudo yum -y install docker docker-compose

Activating the Docker daemon also differs by distribution, but if you have
``systemd``, it looks like this:

.. code-block:: bash

   sudo systemctl start docker   # start ASAP
   sudo systemctl enable docker  # start automatically on startup

Then, enter the ``tests/integration_tests`` directory
and run the ``startup.sh`` script (you must be run **in** that directory and
run the scrip, it's not a very robust script :D).

.. code-block:: bash

   $ cd tests/integration_tests
   $ ./startup.sh

This may take a long time to complete the first time, but there should always be
output indicating that something is happening. This whole thing starts a local
GitLab instance to run tests against.

.. important::

   The GitLab instance may start automatically on startup after running the
   ``startup.sh`` script. To turn it off permanently, run ``docker-compose
   down`` in the ``tests/integration_tests`` directory.

Now the infrastructure needed for the integration tests is there. To actually
run the integration tests, you first need to build the test container. In the
root of the project, run:

.. code-block:: bash

   $ sudo docker build -t repobee:test -f Dockerfile.test .

.. important::

   Every time you change something in the production code, the test container
   must be rebuilt!

Then it's just a matter of running the integration tests (also from the root of
the project).

.. code-block:: bash

   $ sudo REPOBEE_NO_VERIFY_SSL='true' pytest tests/integration_tests/integration_tests.py

This usually takes 10-20 minutes, depending on your hardware. To run just a
subset of the tests, specify the ``-k`` option at the end, and follow with the
name of a test class or a specific test. For example, to *only* run the
TestUpdate class, you add ``-k TestUpdate`` to the end of the above command.

.. note::

   If your user is part of the docker group, you do not need ``sudo`` for the
   ``docker`` and ``docker-compose`` commands.

Code Style
==========
RepoBee follows a fairly strict code style, which is *mostly* enforced by the
:ref:`pre-commit hooks`. So make sure you install them. The code is formatted by
`Black <https://github.com/psf/black>`, and you have no say in that: Black does
it the way it wants. What Black does not handle is docstrings. Any public
function must have a docstring, complete with type annotations and
argument+return value descriptions. Here are two examples:

.. code-block:: python
   :caption: Docstring examples

   def func_without_return_value(int_param: int, string_param: str) -> None:
      """What the function does.

      Args:
         int_param: Description of the int_param.
         string_param: Description of the string_param.
      """

   def func_with_return_value(int_param: int, string_param: str) -> str:
      """What the function does.

      Args:
         int_param: Description of the int_param.
         string_param: Description of the string_param.
      Returns:
         Description of return value.
      """

Contributing to Docs
====================
To be able to build the documentation, you must install the dependencies liste
in ``requirements/docs.txt``, in addition to installing the package itself.
In your virtual environment, run the following from the root of the repository:

.. code-block:: bash

   $ pip install -r requirements/docs.txt

Then, to build the documentation, enter the ``docs`` directory and run ``make html``.

.. code-block:: bash

   $ cd docs
   $ make html

This will produce the documentation in ``docs/_build/html``, with the landing
page being ``docs/_build/html/index.html``.
