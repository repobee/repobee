"""Constants related to template repos."""
import pathlib

from repobee_testhelpers.funcs import hash_directory

TEMPLATE_REPOS_DIR = pathlib.Path(__file__).parent / "template-repos"
TASK_CONTENTS_SHAS = {
    dir_.name: hash_directory(dir_) for dir_ in TEMPLATE_REPOS_DIR.iterdir()
}
TEMPLATE_REPO_NAMES = tuple(
    template.name
    for template in TEMPLATE_REPOS_DIR.iterdir()
    if template.is_dir()
)
