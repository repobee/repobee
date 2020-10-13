import importlib
import itertools
import pathlib
import types

from typing import List

import pkgutil

import sphinx.application

import _repobee.ext


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
    if docname == "builtins":
        header = "Built-in plugins"
        content = [header, "*" * len(header), *process_package(_repobee.ext)]
        source[0] = "\n".join(content)


def process_package(pkg: types.ModuleType) -> List[str]:
    pkg_init_path = pathlib.Path(pkg.__file__)
    if pkg_init_path.name != "__init__.py":
        raise ValueError(f"'{pkg.__name__}' is not a package")

    pkg_dir_path = pkg_init_path.parent

    mods_and_pkgs = [
        (mod, ispkg)
        for _, mod, ispkg in pkgutil.iter_modules([str(pkg_dir_path)])
    ]
    subpackages = [
        importlib.import_module(f"{pkg.__name__}.{subpkg}")
        for subpkg, ispkg in mods_and_pkgs
        if ispkg
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
        map(process_package, subpackages)
    )
    return itertools.chain(mod_sections, subpkg_mod_sections)


def process_module(mod: types.ModuleType) -> List[str]:
    modname = mod.__name__.split(".")[-1]
    docstring_lines = mod.__doc__.split("\n")
    content = [modname, "-" * len(modname), *docstring_lines, "\n"]
    return content
