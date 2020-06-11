import pathlib
import subprocess
import tempfile
import gitlab
import shutil
import time
import sys

from typing import List


CURRENT_DIR = pathlib.Path(__file__).parent
TEACHER = "ric"
STUDENTS = (
    pathlib.Path("students.txt").read_text(encoding="utf8").strip().split("\n")
)
TOKEN = pathlib.Path("token").read_text(encoding="utf8").strip()

MASTER_REPO_GROUP = "dd1337-master"
COURSE_ROUND_GROUP = "dd1337-fall2020"
LOCAL_MASTER_REPOS = list(
    dir_
    for dir_ in (CURRENT_DIR / "dd1337-master-repos").iterdir()
    if dir_.is_dir()
)

DOCKER_START_COMMANDS = [
    "sudo docker-compose up -d",
    "sudo docker exec -it gitlab update-permissions",
    "sudo docker container stop gitlab",
    "sudo docker-compose up -d",
]
DOCKER_VOLUME = CURRENT_DIR / "volume_data"


def setup():
    for cmd in DOCKER_START_COMMANDS:
        subprocess.run(cmd.split(), cwd=CURRENT_DIR)
    if not await_gitlab_started():
        raise OSError("GitLab failed to start")

    create_users(users=STUDENTS + [TEACHER])
    create_teacher_token(teacher=TEACHER, token=TOKEN)
    create_groups_and_projects(
        local_master_repos=LOCAL_MASTER_REPOS,
        teacher=TEACHER,
        master_group_name=MASTER_REPO_GROUP,
        course_round_group_name=COURSE_ROUND_GROUP,
        token=TOKEN,
    )


def teardown():
    subprocess.run("sudo docker-compose down".split(), cwd=CURRENT_DIR)
    subprocess.run(
        f"sudo rm -rf {str(DOCKER_VOLUME)}".split(), cwd=CURRENT_DIR
    )
    subprocess.run(
        f"git checkout {str(DOCKER_VOLUME.relative_to(CURRENT_DIR))}".split(),
        cwd=CURRENT_DIR,
    )


def exec_gitlab_rails_cmd(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*"sudo docker exec -t gitlab gitlab-rails runner".split(), cmd]
    )


def create_users(users: str) -> None:
    print(f"Creating users: {users}")
    create_users_cmd = (
        str(users).replace("'", '"')
        + """
.each do |username|
    User.create(name: username.capitalize, username: username, email: "#{username}@repobee.org", password: "#{username}_pass", skip_confirmation: true).save!
end
""".strip().replace(
            "\n", " "
        )
    )
    exec_gitlab_rails_cmd(create_users_cmd)


def create_teacher_token(teacher: str, token: str) -> None:
    print("Creating teacher's access token")
    create_token_cmd = f"""
user = User.find_by_username('{teacher}')
token = user.personal_access_tokens.create(name: 'repobee', scopes: [:api, :read_repository, :write_repository])
token.set_token('{token}')
token.save!
"""
    exec_gitlab_rails_cmd(create_token_cmd)


def create_groups_and_projects(
    local_master_repos: List[pathlib.Path],
    teacher: str,
    master_group_name: str,
    course_round_group_name: str,
    token: str,
) -> None:
    gl = gitlab.Gitlab(
        "https://gitlab.integrationtest.local",
        private_token=TOKEN,
        ssl_verify=False,
    )

    master_group = gl.groups.create(
        dict(name=master_group_name, path=master_group_name)
    )
    gl.groups.create(
        dict(name=course_round_group_name, path=course_round_group_name)
    )

    for local_repo in local_master_repos:
        project = gl.projects.create(
            dict(
                name=local_repo.name,
                path=local_repo.name,
                description=f"Master repo for {local_repo.name}",
                visibility="private",
                namespace_id=master_group.id,
            )
        )
        authed_project_url = project.attributes["http_url_to_repo"].replace(
            "https://", f"https://oauth2:{TOKEN}@"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repodir = pathlib.Path(tmpdir) / "repo"
            shutil.copytree(src=local_repo, dst=repodir)
            commands = [
                "git init".split(),
                f"git config --local http.sslverify false".split(),
                f"git config --local user.name {teacher.capitalize()}".split(),
                f"git config --local user.email {teacher.capitalize()}@repobee.org".split(),
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
            "sudo docker inspect -f {{.State.Health.Status}} gitlab".split(),
            capture_output=True,
        )
        .stdout.decode(sys.getdefaultencoding())
        .strip()
    )


if __name__ == "__main__":
    main()
