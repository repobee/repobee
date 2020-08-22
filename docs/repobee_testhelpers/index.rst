.. repobee documentation master file, created by
   sphinx-quickstart on Thu Jun 29 18:11:20 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _repobee_testhelpers:

``repobee_testhelpers`` Developer Documentation
===============================================

``repobee_testhelpers`` is a package for assisting in the testing of RepoBee
and plugins. It is meant to be used both by independent plugin developers,
and we strive to make it stable as soon as possible.

Most notably, this package contains an implementation of the
:py:class`repobee_plug.PlatformAPI`, that emulates a GitHub-like platform
locally. This is a boon for testing, and we are working on making it as
user-friendly as possible.

Refer to the module reference for details on the contents of the package.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   code
