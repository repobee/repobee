.. _plug_modref:

``repobee_plug`` Module Reference
**********************************


platform
==========

.. automodule:: repobee_plug.platform
    :members:
    :inherited-members:

localreps
==========

.. automodule:: repobee_plug.localreps
    :members:

exceptions
==========

.. automodule:: repobee_plug.exceptions
    :members:

fileutils
==========

.. automodule:: repobee_plug.fileutils
    :members:

log
==========

.. automodule:: repobee_plug.log
    :members:

name
====

.. automodule:: repobee_plug.name
    :members:

reviews
=======

.. automodule:: repobee_plug.reviews
    :members:

deprecation
===========

.. automodule:: repobee_plug.deprecation
    :members:

serialize
=========

.. automodule:: repobee_plug.serialize
    :members:

cli
===
The ``cli`` subpackage contains the specific parts to extend RepoBee's command
line interface.

.. important::

    The vast majority of the classes and functions of this package can be
    accessed from the ``cli`` package. Canonical usage of most functionality is
    like this:

    .. code-block:: python

        import repobee_plug as plug

        class ExtCommand(plug.Plugin, plug.cli.Command):
            is_awesome = plug.cli.flag(help="whether or not everything is awesome")

            def command(self):
                print(f"Everything is awesome = {self.is_awesome}")

args
----

.. automodule:: repobee_plug.cli.args
    :members:

base
----

.. automodule:: repobee_plug.cli.base
    :members:

categorization
--------------

.. automodule:: repobee_plug.cli.categorization
    :members:

commandmarkers
--------------

.. automodule:: repobee_plug.cli.commandmarkers
    :members:

io
----

.. automodule:: repobee_plug.cli.io
    :members:

settings
--------

.. automodule:: repobee_plug.cli.settings
    :members:

_corehooks
==========

 .. important::

    The ``_corehooks`` module is part of the module reference only for
    specification purposes. Plugin developers should never try to import from
    this module.

.. automodule:: repobee_plug._corehooks
    :members:

_exthooks
==========

 .. important::

    The ``_exthooks`` module is part of the module reference only for
    specification purposes. Plugin developers should never try to import from
    this module.

.. automodule:: repobee_plug._exthooks
    :members:
