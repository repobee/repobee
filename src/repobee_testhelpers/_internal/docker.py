"""Helper functions for running RepoBee in Docker, for the system tests."""
import subprocess
import sys
import shlex

VOLUME_DST = "/workdir"
COVERAGE_VOLUME_DST = "/coverage"


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
    print(docker_command)
    proc = subprocess.run(
        shlex.split(docker_command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(
        proc.stdout.decode(sys.getdefaultencoding())
    )  # for test output on failure
    return proc
