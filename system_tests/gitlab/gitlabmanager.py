import pathlib
import subprocess
import tempfile
import shutil
import time
import sys

from typing import List

import gitlab

from _helpers.const import (
    TEMPLATE_ORG_NAME,
    ORG_NAME,
    TEACHER,
    STUDENT_TEAM_NAMES,
    TOKEN,
    ADMIN_TOKEN,
    TEMPLATE_REPO_PATHS,
)

CURRENT_DIR = pathlib.Path(__file__).parent

BASE_URL = "https://localhost:50443"

DOCKER_START_COMMANDS = [
    "docker network create development",
    "docker-compose up -d",
    "docker exec -it gitlab update-permissions",
    "docker container stop gitlab",
    "docker-compose up -d",
]
DOCKER_VOLUME = CURRENT_DIR / "volume_data"

DOCKER_TEARDOWN_COMMANDS = [
    "docker-compose down",
    "docker network rm development",
    f"rm -rf {str(DOCKER_VOLUME)}",
    f"git checkout {str(DOCKER_VOLUME.relative_to(CURRENT_DIR))}",
]


def main(args: List[str]) -> None:
    def _usage():
        print("usage: python gitlabmanager.py <setup|backup|restore|teardown>")
        sys.exit(1)

    if len(args) != 2:
        _usage()

    cmd = args[1]
    if cmd == "setup":
        setup()
    elif cmd == "backup":
        backup()
    elif cmd == "restore":
        restore()
    elif cmd == "teardown":
        teardown()
    else:
        _usage()


def setup():
    print("Setting up GitLab instance")
    for cmd in DOCKER_START_COMMANDS:
        subprocess.run(cmd.split(), cwd=CURRENT_DIR)
    if not await_gitlab_started():
        raise OSError("GitLab failed to start")

    setup_users(
        students=STUDENT_TEAM_NAMES,
        teacher=TEACHER,
        teacher_token=TOKEN,
        admin_token=ADMIN_TOKEN,
    )


def teardown():
    print("Tearing down GitLab instance")
    for cmd in DOCKER_TEARDOWN_COMMANDS:
        subprocess.run(cmd.split(), cwd=CURRENT_DIR)


def backup():
    print("Creating backup of GitLab instance")
    subprocess.run(
        "docker exec -t gitlab gitlab-backup create".split(), cwd=CURRENT_DIR
    )


def restore():
    delete_groups()
    create_groups_and_projects(
        local_master_repos=TEMPLATE_REPO_PATHS,
        teacher=TEACHER,
        master_group_name=TEMPLATE_ORG_NAME,
        course_round_group_name=ORG_NAME,
        token=TOKEN,
    )


def restart():
    teardown()
    setup()


def exec_gitlab_rails_cmd(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*"docker exec -t gitlab gitlab-rails runner".split(), cmd]
    )


def setup_users(
    students: List[str], teacher: str, teacher_token: str, admin_token: str
) -> None:
    print("Setting up users")
    users = students + [teacher]
    create_users_cmd = (
        str(users).replace("'", '"')
        + """
.each do |username|
    User.create(
        name: username.capitalize,
        username: username,
        email: "#{username}@repobee.org",
        password: "#{username}_pass",
        skip_confirmation: true).save!
end
""".strip().replace(
            "\n", " "
        )
    )
    create_token_cmd = f"""
teacher_user = User.find_by_username('{teacher}')
token = teacher_user.personal_access_tokens.create(
    name: 'repobee',
    scopes: [:api, :read_repository, :write_repository])
token.set_token('{teacher_token}')
token.save!
"""
    set_root_password_cmd = f"""
root_user = User.where(id: 1).first
root_user.password = 'password'
root_user.password_confirmation = 'password'
root_user.save!
token = root_user.personal_access_tokens.create(
    name: 'repobee',
    scopes: [:api, :read_repository, :write_repository, :sudo])
token.set_token('{admin_token}')
token.save!
"""
    compound_cmd = create_users_cmd + create_token_cmd + set_root_password_cmd
    exec_gitlab_rails_cmd(compound_cmd)


def delete_groups() -> None:
    print("Deleting groups")
    delete_groups_cmd = """
Group.all().each { |group| GroupDestroyWorker.perform_async(group.id, 1) }
while not Group.first().nil?
    print('Waiting for groups to be deleted ...\n')
    sleep(1)
end
    """.strip()
    exec_gitlab_rails_cmd(delete_groups_cmd)


def create_groups_and_projects(
    local_master_repos: List[pathlib.Path],
    teacher: str,
    master_group_name: str,
    course_round_group_name: str,
    token: str,
) -> None:
    print("Creating groups and projects")
    gl = gitlab.Gitlab(BASE_URL, private_token=TOKEN, ssl_verify=False)

    master_group = gl.groups.create(
        dict(name=master_group_name, path=master_group_name)
    )
    gl.groups.create(
        dict(name=course_round_group_name, path=course_round_group_name)
    )

    for local_repo in local_master_repos:
        gl.projects.create(
            dict(
                name=local_repo.name,
                path=local_repo.name,
                description=f"Master repo for {local_repo.name}",
                visibility="private",
                namespace_id=master_group.id,
            )
        )
        authed_base_url = BASE_URL.replace(
            "https://", f"https://oauth2:{TOKEN}@"
        )
        authed_project_url = (
            f"{authed_base_url}/{master_group_name}/{local_repo.name}.git"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repodir = pathlib.Path(tmpdir) / "repo"
            shutil.copytree(src=local_repo, dst=repodir)
            commands = [
                "git init".split(),
                "git config --local http.sslverify false".split(),
                f"git config --local user.name {teacher.capitalize()}".split(),
                (
                    f"git config --local user.email {teacher.capitalize()}"
                    f"@repobee.org".split()
                ),
                "git add .".split(),
                [*"git commit -m".split(), "'Add task template'"],
                f"git push {authed_project_url} master".split(),
            ]
            for cmd in commands:
                subprocess.run(cmd, cwd=str(repodir))


def await_gitlab_started() -> bool:
    status = get_gitlab_status()
    while status != "healthy":
        if status == "unhealthy":
            return False

        time.sleep(5)
        status = get_gitlab_status()

        print(f"GitLab status: {status} ...")

    return True


def get_gitlab_status():
    return (
        subprocess.run(
            "docker inspect -f {{.State.Health.Status}} gitlab".split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        .stdout.decode(sys.getdefaultencoding())
        .strip()
    )


if __name__ == "__main__":
    main(sys.argv)
