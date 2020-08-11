"""This module serves only to distinguish whether or not RepoBee has been
installed with RepoBee's distribution tools, or on any other way (e.g.  pip,
locally etc). This allows us to enable certain features only for installed
RepoBee.
"""
import pathlib
import typing

DIST_INSTALL: bool = False
INSTALL_DIR: typing.Optional[pathlib.Path] = None
