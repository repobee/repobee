"""Constants used in the integration tests."""
import pathlib

import repobee_plug as plug

VOLUME_DST = "/workdir"
COVERAGE_VOLUME_DST = "/coverage"
DIR = pathlib.Path(__file__).resolve().parent
TOKEN = (DIR.parent / "token").read_text(encoding="utf-8").strip()
OAUTH_USER = "oauth2"
BASE_DOMAIN = "gitlab.integrationtest.local"
BASE_URL = "https://" + BASE_DOMAIN
LOCAL_DOMAIN = "localhost:50443"
LOCAL_BASE_URL = "https://" + LOCAL_DOMAIN
ORG_NAME = "dd1337-fall2020"
MASTER_ORG_NAME = "dd1337-master"
TEACHER = "ric"
MASTER_REPO_NAMES = [
    p.name
    for p in (DIR.parent / "dd1337-master-repos").iterdir()
    if p.is_dir()
]
STUDENT_TEAMS = [
    plug.StudentTeam(members=[s.strip()])
    for s in (DIR.parent / "students.txt").read_text().strip().split("\n")
]
STUDENT_TEAM_NAMES = [str(t) for t in STUDENT_TEAMS]
STUDENT_REPO_NAMES = plug.generate_repo_names(STUDENT_TEAMS, MASTER_REPO_NAMES)
REPOBEE_GITLAB = "repobee -p gitlab"
BASE_ARGS_NO_TB = ["--bu", BASE_URL, "-o", ORG_NAME, "-t", TOKEN]
BASE_ARGS = [*BASE_ARGS_NO_TB, "--tb"]
STUDENTS_ARG = ["-s", " ".join(STUDENT_TEAM_NAMES)]
MASTER_REPOS_ARG = ["--mn", " ".join(MASTER_REPO_NAMES)]
MASTER_ORG_ARG = ["--mo", MASTER_ORG_NAME]
TASK_CONTENTS_SHAS = {
    "task-1": b"\xb0\xb0,t\xd1\xe9a bu\xdfX\xcf,\x98\xd2\x04\x1a\xe8\x88",
    "task-2": b"\x1d\xdc\xa6A\xd7\xec\xdc\xc6FSN\x01\xdf|\x95`U\xb5\xdc\x9d",
    "task-3": b"Q\xd1x\x13r\x02\xd9\x98\xa2\xb2\xd9\xe3\xa9J^\xa2/X\xbe\x1b",
}
