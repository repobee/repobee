.. _docker_usage:

Using RepoBee with Docker
*************************

RepoBee offers a minimal Docker image backed by Alpine Linux that weighs in at
less than 100 MB, and `can be found here
<https://hub.docker.com/r/repobee/repobee>`_. Usage with Docker is mostly the
same as with a local install, but there are some significant differences in how
to get started. This part of the user guide outlines how to use RepoBee with
Docker as efficiently as possible.

.. note::

    For frequent users of RepoBee, we recommend installing it locally for an
    optimal user experience. The Docker image is useful for trying out RepoBee
    without installing anything (other than Docker), as well as for creating
    automation scripts, but the CLI is noticeably less responsive compared to
    installing RepoBee directly on the host machine.

Basic usage
-----------

There are two primary ways to use RepoBee in Docker: through an interactive
``bash`` session in which you can operate as per-usual, or by issuing
individual commands through Docker.

.. note::

    Running the ``docker`` program requires root privilege unless you are part
    of the ``docker`` group. Depending on how your system is configured, you
    may need to prepend ``sudo`` to all ``docker`` commands in this guide.

Using RepoBee in an interactive ``bash`` session
++++++++++++++++++++++++++++++++++++++++++++++++

The primary way of using RepoBee in Docker is through an interactive ``bash``
session within a Docker container. Here's a simple example of checking the
version number of RepoBee.

.. code-block:: bash
    :caption: Starting an interactive ``bash`` shell in a RepoBee Docker
        container

    $ docker run --rm -it repobee/repobee \
        /bin/bash
    bash5.1$ repobee --version
    v3.7.0-dev

In further listings, we'll use the prefix ``bash-5.1$`` to denote that we're
*inside* the Docker container. Once in the session, you can use RepoBee mostly
as described in the rest of this user guide, with a few exceptions in regards
to installing plugins and managing the installation. Note also that we always
do a line-break in the Docker command, and specify the command to run inside
Docker on a separate line (here ``/bin/bash``). This is for added clarity, and
nothing you need to do yourself.

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

    $ docker run --rm -it repobee/repobee:v3.6.0 \
        /bin/bash
    bash-5.1$ repobee --version
    v3.6.0

We will omit the version tag throughout this guide, but keep in mind that you
should always specify a version tag when using RepoBee in practice.

Running a single RepoBee command
++++++++++++++++++++++++++++++++

If you just want to run a single command, you don't need to run ``bash``,
but can run the RepoBee command directly. For example, we could run ``repobee
--version`` like so.

.. code-block:: bash
    :caption: Running ``repobee --version`` without first starting a bash
        shell

    $ docker run --rm -it repobee/repobee \
        repobee --version

In several of the following examples, we will execute single commands like
the one shown above, without starting a ``bash`` session. In practice, it's
however most often more convenient to start an interactive bash session and
then execute RepoBee commands in there.

Working directory and config file
---------------------------------

To make effective use of RepoBee in Docker, you need to be able to persist
data, most importantly a configuration file. The default working directory of
the RepoBee image is ``/home/repobee/workdir``. With the recent addition of
local config files (see :ref:`local_config`), the simplest way to configure
RepoBee in Docker is to mount a named volume at ``/home/repobee/workdir`` and
create a local config file in it with the ``config wizard`` command.

.. code-block:: bash
    :caption: Using a named volume called ``repobee-workdir`` for persistent storage

    $ docker run --rm -v repobee-workdir:/home/repobee/workdir -it repobee/repobee \
        repobee --config-file repobee.ini config wizard
    # follow the prompts to configure RepoBee

Now, the next time you run Docker with this volume mounted in the same place,
RepoBee will pick up the local ``repobee.ini`` config file. Note that you don't
need to specify ``repobee.ini`` as the config file after having created it, due
to how local config files work in RepoBee.

.. code-block:: bash

    $ docker run --rm -v repobee-workdir:/home/repobee -it repobee/repobee \
        repobee config show
    # should show the config

While you *can* access the named volume, which is typically located at
``/var/lib/docker/volumes/<VOLUME_NAME>``, we recommend working with it only
through Docker. Otherwise, issues with file and directory permissions may
spring up which require some Docker and UNIX know-how to solve.

.. important::

    If you don't specify the volume when running a RepoBee container, none of
    your previously stored data will be available, including the config file!

If for some reason you have a need to frequently access the data inside the
storage volume outside of the Docker container, it's typically often a better
idea to use a local directory instead. Here's an example of how to do that.

.. code-block:: bash

    $ mkdir repobee-workdir # create local directory
    $ chown 1000:1000 repobee-workdir # set UID:GID to match the image's repobee user
    $ docker run --rm -v "$PWD/repobee-workdir":/home/repobee/workdir -it repobee/repobee \
        /bin/bash
    bash-5.1$ # do stuff

If your host machine's user ID and group ID do not match the user ID and group
ID of the image's user (both of wich are 1000), you may be unable to modify
content in the working directory without ``sudo``. You should however be able
to read all content regardless.

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

    FROM repobee/repobee # Optionally, append version tag (e.g. :v3.6.0)

    RUN repobee plugin install --version-spec junit4@v1.2.1
    RUN repobee plugin install --version-spec csvgrades@v0.2.1

Given that the Dockerfile is in the current directory, you can then build the
image and run a container from it it like so.

.. code-block:: bash
    :caption: Building and executing a custom RepoBee Docker image

    $ docker build -t my-repobee-img .
    $ docker run --rm -it my-repobee-img \
        repobee plugin list
    # should show that junit4 and csvgrades are installed
