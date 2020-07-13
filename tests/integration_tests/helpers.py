import pathlib
import hashlib
import tempfile
import os
import sys
import subprocess

import gitlab
import repobee_plug as plug

import _repobee.ext.gitlab

VOLUME_DST = "/workdir"
COVERAGE_VOLUME_DST = "/coverage"
DIR = pathlib.Path(__file__).resolve().parent
TOKEN = (DIR / "token").read_text(encoding="utf-8").strip()

OAUTH_USER = "oauth2"
BASE_DOMAIN = "gitlab.integrationtest.local"
BASE_URL = "https://" + BASE_DOMAIN
LOCAL_DOMAIN = "localhost:50443"
LOCAL_BASE_URL = "https://" + LOCAL_DOMAIN
ORG_NAME = "dd1337-fall2020"
MASTER_ORG_NAME = "dd1337-master"
ACTUAL_USER = "ric"

MASTER_REPO_NAMES = [
    p.name for p in (DIR / "dd1337-master-repos").iterdir() if p.is_dir()
]
STUDENT_TEAMS = [
    plug.Team(members=[s.strip()])
    for s in pathlib.Path("students.txt").read_text().strip().split("\n")
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


def api_instance(org_name=ORG_NAME):
    """Return a valid instance of the GitLabAPI class."""
    return _repobee.ext.gitlab.GitLabAPI(LOCAL_BASE_URL, TOKEN, org_name)


def gitlab_and_groups():
    """Return a valid gitlab instance, along with the master group and the
    target group.
    """
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    master_group = gl.groups.list(search=MASTER_ORG_NAME)[0]
    target_group = gl.groups.list(search=ORG_NAME)[0]
    return gl, master_group, target_group


def run_in_docker_with_coverage(command, extra_args=None):
    assert extra_args, "extra volume args are required to run with coverage"
    coverage_command = (
        "coverage run --branch --append --source _repobee -m " + command
    )
    return run_in_docker(coverage_command, extra_args=extra_args)


def run_in_docker(command, extra_args=None):
    extra_args = " ".join(extra_args) if extra_args else ""
    docker_command = (
        "sudo docker run {} --net development --rm --name repobee "
        "repobee:test /bin/sh -c '{}'"
    ).format(extra_args, command)
    proc = subprocess.run(
        docker_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(proc.stdout.decode(sys.getdefaultencoding())) # for test output on failure
    return proc


def update_repo(repo_name, filename, text):
    """Add a file with the given filename and text to the repo."""
    gl = gitlab.Gitlab(LOCAL_BASE_URL, private_token=TOKEN, ssl_verify=False)
    proj, *_ = [
        p for p in gl.projects.list(search=repo_name) if p.name == repo_name
    ]
    env = os.environ.copy()
    env["GIT_SSL_NO_VERIFY"] = "true"
    env["GIT_AUTHOR_EMAIL"] = "slarse@kth.se"
    env["GIT_AUTHOR_NAME"] = "Simon"
    env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]
    env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
    with tempfile.TemporaryDirectory() as tmpdir:
        url_with_token = (
            proj.web_url.replace(
                "https://", "https://oauth2:{}@".format(TOKEN)
            ).replace(BASE_DOMAIN, LOCAL_DOMAIN)
            + ".git"
        )
        clone_proc = subprocess.run(
            "git clone {}".format(url_with_token).split(), cwd=tmpdir, env=env
        )
        assert clone_proc.returncode == 0

        repo_dir = pathlib.Path(tmpdir) / proj.name
        new_file = repo_dir / filename
        new_file.touch()
        new_file.write_text(text)

        add_proc = subprocess.run(
            "git add {}".format(filename).split(), cwd=str(repo_dir), env=env
        )
        assert add_proc.returncode == 0

        commit_proc = subprocess.run(
            "git commit -am newfile".split(), cwd=str(repo_dir), env=env
        )
        assert commit_proc.returncode == 0

        push_proc = subprocess.run(
            "git push".split(), cwd=str(repo_dir), env=env
        )
        assert push_proc.returncode == 0

    assert proj.files.get(filename, "master").decode().decode("utf8") == text

def hash_directory(path):
    shas = []
    for dirpath, _, filenames in os.walk(str(path)):
        if ".git" in dirpath:
            continue
        files = list(
            pathlib.Path(dirpath) / filename for filename in filenames
        )
        shas += (hashlib.sha1(file.read_bytes()).digest() for file in files)
    return hashlib.sha1(b"".join(sorted(shas))).digest()


