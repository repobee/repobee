import pathlib
import shutil
import sys
import os
import subprocess
import shlex
import time
import json
import tempfile
import itertools

from typing import List

import requests

import repobee_plug as plug

import repobee_testhelpers._internal.templates as template_helpers

CURRENT_DIR = pathlib.Path(__file__).parent

TARGET_ORG_NAME = "course-fall-2020"
TEMPLATE_ORG_NAME = "template-repos"

BASE_URL = "https://localhost:3000"
API_URL = f"{BASE_URL}/api/v1"
LOCAL_TEMPLATE_REPOS = list(
    dir_.absolute() for dir_ in template_helpers.TEMPLATE_REPOS_DIR.iterdir()
)

COMPOSE_FILE_TEMPLATE = CURRENT_DIR / "docker-compose.yml.template"
COMPOSE_FILE_OUTPUT = CURRENT_DIR / "docker-compose.yml"
DOCKER_VOLUME = CURRENT_DIR / "gitea"
DOCKER_START_COMMANDS = [
    "docker network create development",
    "docker-compose up -d",
]
REPOSITORIES_ROOT = DOCKER_VOLUME / "git" / "repositories"

DOCKER_TEARDOWN_COMMANDS = [
    "docker-compose down",
    "docker network rm development",
    f"rm -rf {str(DOCKER_VOLUME)}",
    f"git checkout {DOCKER_VOLUME}",
]

TEACHER_USER = "teacher"
TEACHER_TOKEN = (
    (CURRENT_DIR / "teacher_token.txt").read_text(encoding="utf8").strip()
)

ADMIN_TOKEN = (
    (CURRENT_DIR / "admin_token.txt").read_text(encoding="utf8").strip()
)

STUDENT_TEAMS = [
    plug.StudentTeam(members=line.strip().split())
    for line in (CURRENT_DIR / "students.txt")
    .read_text("utf8")
    .strip()
    .split("\n")
]


def main(args: List[str]) -> None:
    def _usage():
        print("usage: python giteamanager.py <prime|setup|teardown>")
        sys.exit()

    if len(args) != 2:
        _usage()

    cmd = args[1]
    if cmd == "prime":
        prime()
    elif cmd == "setup":
        setup()
    elif cmd == "teardown":
        teardown()
    else:
        _usage()


def prime():
    if os.getuid() == 0:
        raise RuntimeError("prime must be run as non-root")

    print(f"Creating {COMPOSE_FILE_OUTPUT}")
    modified_compose_content = (
        COMPOSE_FILE_TEMPLATE.read_text("utf8")
        .replace("<REPLACE_UID>", str(os.getuid()))
        .replace("<REPLACE_GID>", str(os.getgid()))
    )
    COMPOSE_FILE_OUTPUT.write_text(modified_compose_content, encoding="utf8")
    print("Done!")


def setup():
    if gitea_is_running():
        teardown()

    print("Setting up Gitea instance")
    for cmd in DOCKER_START_COMMANDS:
        subprocess.run(shlex.split(cmd), cwd=CURRENT_DIR)

    if not await_gitea_start():
        print("failed to start Gitea instance", file=sys.stderr)
        teardown()
        sys.exit(1)

    print("Setting up organizations")
    create_private_organization(TARGET_ORG_NAME, token=TEACHER_TOKEN)
    create_private_organization(TEMPLATE_ORG_NAME, token=TEACHER_TOKEN)

    for local_repo in LOCAL_TEMPLATE_REPOS:
        gitea_request(
            requests.post,
            f"/orgs/{TEMPLATE_ORG_NAME}/repos",
            TEACHER_TOKEN,
            data=dict(
                name=local_repo.name,
                visibility="private",
                description=f"Template repo for {local_repo.name}",
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repodir = pathlib.Path(tmpdir) / "repo"
            shutil.copytree(src=local_repo, dst=repodir)

            authed_base_url = BASE_URL.replace(
                "https://", f"https://{TEACHER_USER}:{TEACHER_TOKEN}@"
            )
            authed_project_url = (
                f"{authed_base_url}/{TEMPLATE_ORG_NAME}/{local_repo.name}"
            )

            commands = [
                "git init".split(),
                "git config --local http.sslverify false".split(),
                f"git config --local "
                f"user.name {TEACHER_USER.capitalize()}".split(),
                (
                    f"git config --local "
                    f"user.email {TEACHER_USER.capitalize()}"
                    f"@repobee.org".split()
                ),
                "git add .".split(),
                [*"git commit -m".split(), "'Add task template'"],
                f"git push {authed_project_url} master".split(),
            ]
            for cmd in commands:
                subprocess.run(cmd, cwd=str(repodir))

    for member in itertools.chain.from_iterable(
        [t.members for t in STUDENT_TEAMS]
    ):
        create_user(member)


def teardown():
    print("Tearing down Gitea instance")
    for cmd in DOCKER_TEARDOWN_COMMANDS:
        subprocess.run(shlex.split(cmd), cwd=CURRENT_DIR)


def gitea_request(
    request_func,
    endpoint: str,
    token: str,
    api_base_url: str = API_URL,
    **kwargs,
):
    url = f"{api_base_url}/{endpoint.lstrip('/')}"
    authed_kwargs = dict(
        headers={
            "Authorization": f"token {token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        verify=False,
        **kwargs,
    )
    if "data" in authed_kwargs:
        authed_kwargs["data"] = json.dumps(authed_kwargs["data"])

    resp = request_func(url, **authed_kwargs)

    if resp.status_code not in [200, 201]:
        raise RuntimeError(
            f"unexpected response: {resp} -- {resp.content.decode('utf8')}"
        )


def await_gitea_start() -> bool:
    tries = 0
    max_tries = 1000
    while tries < max_tries:
        time.sleep(0.1)
        if gitea_is_running():
            return True
        tries += 1
    return False


def gitea_is_running() -> bool:
    try:
        response = requests.get(BASE_URL, verify=False)
        print(response)
        return response.status_code == requests.codes.OK
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
        return False


def create_user(username: str) -> None:
    data = {
        "email": f"{username}@repobee.org",
        "full_name": username.capitalize(),
        "login_name": username,
        "must_change_password": False,
        "password": username,
        "send_notify": False,
        "username": username,
    }
    gitea_request(
        requests.post, endpoint="/admin/users", data=data, token=ADMIN_TOKEN
    )


def create_private_organization(org_name: str, token: str) -> None:
    data = {
        "description": "An organization",
        "repo_admin_change_team_access": True,
        "username": org_name,
        "visibility": "private",
    }
    gitea_request(requests.post, endpoint="/orgs", token=token, data=data)


if __name__ == "__main__":
    main(sys.argv)
