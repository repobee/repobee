"""This Sphinx extension preprocesses any doc source file that starts with a
line on the following form.

GENERATE-PACKAGE-DOCS:<package_name>

The line is removed from the file, and the docstrings of the modules in package
<package_name> are appended to the file like so (without the backticks).

```
<module_name>
-------------
<docstring>
```

This applies recursively to modules in subpackages of <package_name>.
"""

import importlib
import itertools
import pathlib
import types

from typing import List

import pkgutil

import sphinx.application

GENERATE_TAG = "GENERATE-PACKAGE-DOCS"


def setup(app: sphinx.application.Sphinx):
    app.connect("source-read", source_read)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": False,
    }


def source_read(
    app: sphinx.application.Sphinx, docname: str, source: List[str]
):
    if source[0].strip().startswith(GENERATE_TAG):
        first_line, *rest = source[0].strip().split("\n")
        _, package_name = first_line.split(":")
        content = [*rest, "\n", *process_package(package_name)]
        source[0] = "\n".join(content)


def process_package(pkg_qualname: types.ModuleType) -> List[str]:
    pkg = importlib.import_module(pkg_qualname)
    pkg_init_path = pathlib.Path(pkg.__file__)
    if pkg_init_path.name != "__init__.py":
        raise ValueError(f"'{pkg.__name__}' is not a package")

    pkg_dir_path = pkg_init_path.parent

    mods_and_pkgs = [
        (mod, ispkg)
        for _, mod, ispkg in pkgutil.iter_modules([str(pkg_dir_path)])
    ]
    subpackage_names = [
        f"{pkg_qualname}.{subpkg}" for subpkg, ispkg in mods_and_pkgs if ispkg
    ]

    mods = [
        importlib.import_module(f"{pkg.__name__}.{mod}")
        for mod, ispkg in mods_and_pkgs
        if not ispkg
    ]

    mod_sections = itertools.chain.from_iterable(
        [process_module(mod) for mod in mods]
    )
    subpkg_mod_sections = itertools.chain.from_iterable(
        map(process_package, subpackage_names)
    )
    return itertools.chain(mod_sections, subpkg_mod_sections)


def process_module(mod: types.ModuleType) -> List[str]:
    modname = mod.__name__.split(".")[-1]
    docstring_lines = mod.__doc__.split("\n")
    label = f".. _builtin_plugin_{modname}:\n\n"
    content = [label, modname, "-" * len(modname), *docstring_lines, "\n"]
    return content
