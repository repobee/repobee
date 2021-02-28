.. _using_docker:

Using RepoBee with Docker
*************************

RepoBee offers a minimal Docker image backed by Alpine Linux that weighs in at
less than 100 MB, and `can be found here
<https://hub.docker.com/r/repobee/repobee>`_. Usage with Docker is mostly the
same as with a local install, but there are some significant differences in how
to get started, and how to

This part of the user guide
outlines how to use RepoBee with Docker.

.. note::

    For frequent users of RepoBee, we recommend installing it locally for an
    optimal user experience. This Docker image is useful for trying out RepoBee
    without installing anything (other than Docker), as well as for creating
    automation scripts, but the CLI is noticeably more sluggish compared to
    installing RepoBee directly on the host machine.

Basic usage
-----------

The most basic usage of RepoBee with docker is to *pull* the image and then
execute an interactive ``bash`` shell inside the container. Here's a simple
example.

.. code-block:: bash
    :caption: Starting an interactive ``bash`` shell in a RepoBee Docker
        container

    $ docker run -it repobee/repobee \
        /bin/bash
    bash5.1$ repobee --version
    v3.7.0-dev

This will open an interactive ``bash`` session in which the ``repobee`` command
is available. In further listings, we'll use the prefix ``bash-5.1$`` to denote
that we're *inside* the Docker container. Note that we also always do a
line-break in the Docker command, and specify the command to run inside Docker
on a separate line. This is for added clarity, and nothing you need to do
yourself.

Note that pulling and running ``repobee/repobee`` without specifying a version
will use the ``latest`` tag, which points to the most recent uploaded image.
This is most often **not a stable release** (in this case, it's an
in-development version of RepoBee 3.7). To use a stable release, you must also
specify a version number, which you can find among the `tags here
<https://hub.docker.com/r/repobee/repobee/tags?page=1&ordering=last_updated>`_.
For example, to use ``v3.6.0``, the command would look like so:

.. code-block:: bash
    :caption: Starting an interactive ``bash`` shell with a stable release of
        RepoBee in Docker

    $ docker run -it repobee/repobee:v3.6.0 \
        /bin/bash
    bash-5.1$ repobee --version
    v3.6.0

We will omit the version tag throughout this guide, but keep in mind that you
should always specify a version tag when using RepoBee in practice.

If you just want to run a single command, you don't need to run ``bash``,
but can run the RepoBee command directly. For example, we could run ``repobee
--version`` like so.

.. code-block:: bash
    :caption: Running ``repobee --version`` without first starting a bash
        shell

    $ docker run -it repobee/repobee \
        repobee --version

In several of the following examples, we will execute single commands like
the one shown above, without starting a ``bash`` session. In practice, it's
however most often more convenient to start an interactive bash session and
then execute RepoBee commands in there.

To make effective use of RepoBee in Docker, there are a few more pieces to the
puzzle, most importantly being able to have a persistent config file, data and
plugins.

Working directory and config file
---------------------------------

The default working directory of the RepoBee image is
``/home/repobee/workdir``. With the recent addition of directory-local config
files (see :ref:`local_config`), the simplest way to configure RepoBee in
Docker is to mount a named volume at ``/home/repobee/workdir`` and create a
directory-local config file in it with the ``config wizard`` command.

.. code-block:: bash
    :caption: Using a named volume called ``repobee-workdir`` for persistent storage

    $ docker run -v repobee-workdir:/home/repobee/workdir -it repobee/repobee \
        repobee -c repobee.ini config wizard
    # follow the prompts to configure RepoBee

Now, the next time you run Docker with this volume mounted in the same place,
RepoBee will pick up the local ``repobee.ini`` config file.

.. code-block:: bash

    $ docker run -v repobee-workdir:/home/repobee -it repobee/repobee \
        repobee config show
    # should show the config

While you *can* access the named volume, which is typically located at
``/var/lib/docker/volumes/<VOLUME_NAME>``, we recommend working with it only
through Docker. Otherwise, issues with file and directory permissions may
spring up which require some Docker and UNIX know-how to solve.

.. important::

    If you don't specify the volume when running a RepoBee container, none of
    your previously stored data will be available, including the config file!

Installing plugins
------------------

It's entirely possible to install plugins while in an interactive ``bash``
session in RepoBee's default Docker image, but you will have to install the
plugin each time you start the container, as the install directory is not
persisted. To *not* have to repeat plugin installations over and over again,
you can instead create your own Dockerfile in which you do so. For example,
the following Dockerfile installs the ``junit4`` and ``csvgrades`` plugins.

.. code-block:: docker
    :caption: Dockerfile that installs junit4 and csvgrades plugins

    FROM repobee/repobee

    RUN repobee plugin install --version-spec junit4@v1.2.1
    RUN repobee plugin install --version-spec csvgrades@v0.2.1

Given that the Dockerfile is in the current directory, you can then build it
like so.

.. code-block:: bash
    :caption: Building and executing a custom RepoBee Docker image

    $ docker build -t my-repobee-img .
    $ docker run -it my-repobee-img \
        repobee plugin list
    # should show that junit4 and csvgrades are installed
