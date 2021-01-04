"""Constants related to template repos."""
import pathlib

from repobee_testhelpers.funcs import hash_directory

TASK_CONTENTS_SHAS = {
    "task-1": b"\xb0\xb0,t\xd1\xe9a bu\xdfX\xcf,\x98\xd2\x04\x1a\xe8\x88",
    "task-2": b"\x1d\xdc\xa6A\xd7\xec\xdc\xc6FSN\x01\xdf|\x95`U\xb5\xdc\x9d",
    "task-3": b"Q\xd1x\x13r\x02\xd9\x98\xa2\xb2\xd9\xe3\xa9J^\xa2/X\xbe\x1b",
}
TEMPLATE_REPOS_DIR = pathlib.Path(__file__).parent / "template-repos"
TASK_CONTENTS_SHAS = {
    dir_.name: hash_directory(dir_) for dir_ in TEMPLATE_REPOS_DIR.iterdir()
}
