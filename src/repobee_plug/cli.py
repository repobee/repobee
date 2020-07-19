"""Plugin functionality for creating extensions to the RepoBee CLI."""
import collections


Option = collections.namedtuple(
    "Option",
    [
        "short_name",
        "long_name",
        "configurable",
        "help",
        "converter",
        "required",
        "default",
        "argparse_kwargs",
    ],
)
Option.__new__.__defaults__ = (None,) * len(Option._fields)
