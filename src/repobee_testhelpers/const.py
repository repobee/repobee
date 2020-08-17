"""Constants for use in tests."""
import pathlib

from repobee_plug import fileutils

TARGET_ORG_NAME = "fall2020"
TEMPLATE_ORG_NAME = "templates"

CUR_DIR = pathlib.Path(__file__).absolute().parent
TEMPLATE_REPO_DIR = CUR_DIR / "resources" / TEMPLATE_ORG_NAME
TEMPLATE_REPO_NAMES = [
    d.name for d in TEMPLATE_REPO_DIR.iterdir() if d.is_dir()
]
TEMPLATE_REPOS_ARG = " ".join(TEMPLATE_REPO_NAMES)

TEACHER = "ric"
STUDENTS_FILE = CUR_DIR / "resources" / "students.txt"
STUDENT_TEAMS = fileutils.parse_students_file(STUDENTS_FILE)

TOKEN = "123token456"
