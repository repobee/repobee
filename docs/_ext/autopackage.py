import types
import pathlib
import importlib
from typing import List

import pkgutil

import sphinx.application
from docutils import nodes
from docutils.statemachine import StringList
from docutils.parsers.rst.states import RSTState
from sphinx.util.docutils import SphinxDirective, switch_source_input
from sphinx.util.nodes import nested_parse_with_titles

from sphinx.ext.napoleon.docstring import GoogleDocstring


class PackageDocstringDirective(SphinxDirective):
    has_content = True

    def run(self):
        content = []
        sections = expand_package_node(
            self.content[0], app=self.env.app, state=self.state
        )

        for section in sections:
            content += nodes.target(
                "",
                "",
                ids=[
                    f"builtin-plugin-{self.env.new_serialno('builtin-plugin')}"
                ],
            )
            content += section

        return content


def purge_packages(app, env, docname):
    if not hasattr(env, "package_all_packages"):
        return

    env.package_all_packages = [
        pkg for pkg in env.package_all_packages if pkg["docname"] != docname
    ]


def merge_packages(app, env, docnames, other):
    env.package_all_packages = getattr(env, "package_all_packages", [])
    if hasattr(other, "package_all_packages"):
        env.package_all_packages.extend(other.package_all_packages)


def expand_package_node(
    pkg_qualname: str, app: sphinx.application.Sphinx, state: RSTState
) -> nodes.section:
    env = app.builder.env
    env.package_all_packages = getattr(env, "package_all_packages", [])

    content = process_package(pkg_qualname, app=app, state=state)

    return content


def process_package(
    pkg_qualname: str, app: sphinx.application.Sphinx, state: RSTState
) -> List[nodes.section]:
    pkg = importlib.import_module(pkg_qualname)
    pkg_init_path = pathlib.Path(pkg.__file__)
    if pkg_init_path.name != "__init__.py":
        raise ValueError(f"'{pkg_qualname}' is not a package")

    pkg_dir_path = pkg_init_path.parent

    mods_and_pkgs = [
        (mod, ispkg) for _, mod, ispkg in pkgutil.iter_modules([pkg_dir_path])
    ]
    mods = [
        importlib.import_module(f"{pkg_qualname}.{mod}")
        for mod, ispkg in mods_and_pkgs
        if not ispkg
    ]
    #    pkg_qualnames = [
    #        f"{pkg_qualname}.{pkg}" for pkg, ispkg in mods_and_pkgs if ispkg
    #    ]

    mod_sections = [process_module(mod, app, state) for mod in mods]
    return mod_sections


def process_module(
    mod: types.ModuleType, app: sphinx.application.Sphinx, state: RSTState
) -> nodes.section:
    sec = nodes.section()

    title = nodes.title()
    title += nodes.Text(mod.__name__.split(".")[-1])

    docstring_lines = mod.__doc__.split("\n")
    processed_docstring_lines = StringList(
        GoogleDocstring(
            docstring_lines, app.config, app, "module", mod.__name__, mod, None
        ).lines()
    )

    sec += title
    sec += parse_docstring(state=state, content=processed_docstring_lines)

    return sec


def parse_docstring(state: RSTState, content: StringList) -> List[nodes.Node]:
    with switch_source_input(state, content):
        sec = nodes.section()
        sec.document = state.document
        nested_parse_with_titles(state, content, sec)
    return sec.children


def setup(app):
    app.add_directive("package", PackageDocstringDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": False,
    }
