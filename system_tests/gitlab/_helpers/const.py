"""Constants used in the integration tests."""
import pathlib

import repobee_plug as plug

from repobee_testhelpers._internal.templates import TEMPLATE_REPOS_DIR


VOLUME_DST = "/workdir"
COVERAGE_VOLUME_DST = "/coverage"
DIR = pathlib.Path(__file__).resolve().parent
TOKEN = (DIR.parent / "token").read_text(encoding="utf-8").strip()
ADMIN_TOKEN = "".join(reversed(TOKEN))
OAUTH_USER = "oauth2"
BASE_DOMAIN = "gitlab.integrationtest.local"
BASE_URL = "https://" + BASE_DOMAIN
LOCAL_DOMAIN = "localhost:50443"
LOCAL_BASE_URL = "https://" + LOCAL_DOMAIN
ORG_NAME = "dd1337-fall2020"
TEMPLATE_ORG_NAME = "dd1337-master"
TEACHER = "ric"
assignment_names = [p.name for p in TEMPLATE_REPOS_DIR.iterdir() if p.is_dir()]
TEMPLATE_REPO_PATHS = list(
    dir_.absolute() for dir_ in TEMPLATE_REPOS_DIR.iterdir() if dir_.is_dir()
)
STUDENT_TEAMS = [
    plug.StudentTeam(members=[s.strip()])
    for s in (DIR.parent / "students.txt").read_text().strip().split("\n")
]
STUDENT_TEAM_NAMES = [str(t) for t in STUDENT_TEAMS]
STUDENT_REPO_NAMES = plug.generate_repo_names(STUDENT_TEAMS, assignment_names)
REPOBEE_GITLAB = "repobee -p gitlab"
BASE_ARGS_NO_TB = ["--bu", BASE_URL, "-o", ORG_NAME, "-t", TOKEN]
BASE_ARGS = [*BASE_ARGS_NO_TB, "--tb"]
STUDENTS_ARG = ["-s", " ".join(STUDENT_TEAM_NAMES)]
MASTER_REPOS_ARG = ["-a", " ".join(assignment_names)]
TEMPLATE_ORG_ARG = ["--template-org-name", TEMPLATE_ORG_NAME]
