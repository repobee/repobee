import os
import subprocess
from unittest.mock import call
from collections import namedtuple
import pathlib

import pytest

from _repobee import git
from _repobee import exception
from _repobee import util

URL_TEMPLATE = "https://{}github.com/slarse/clanim"
REPO_NAME = "clanim"

Env = namedtuple("Env", ("expected_url",))

RunTuple = namedtuple("RunTuple", ("returncode", "stdout", "stderr"))
AioSubproc = namedtuple("AioSubproc", ("create_subprocess", "process"))


@pytest.fixture(autouse=True)
def mock_ensure_repo_dir_exists(mocker, request):
    """Mocked out to not accidentally create directories all over the place."""
    if "no_ensure_repo_dir_mock" in request.keywords:
        return

    mocker.patch("pathlib.Path.mkdir", autospec=True)
    mocker.patch("_repobee.git._git_init", autospec=True)


@pytest.fixture(scope="function")
def env_setup(mocker):
    mocker.patch(
        "subprocess.run", autospec=True, return_value=RunTuple(0, b"", b"")
    )
    return Env(expected_url=URL_TEMPLATE.format(""))


@pytest.fixture(scope="function")
def aio_subproc(mocker):
    class Process:
        async def communicate(self):
            return self.stdout, self.stderr

        stdout = b"this is stdout"
        stderr = b"this is stderr"
        returncode = 0

    async def mock_gen(*args, **kwargs):
        return Process()

    create_subprocess = mocker.patch(
        "asyncio.create_subprocess_exec", side_effect=mock_gen
    )
    return AioSubproc(create_subprocess, Process)


@pytest.fixture
def non_zero_aio_subproc(mocker):
    """asyncio.create_subprocess mock with non-zero exit status."""

    class Process:
        async def communicate(self):
            return b"this is stdout", b"this is stderr"

        returncode = 1

    async def mock_gen(*args, **kwargs):
        return Process()

    create_subprocess = mocker.patch(
        "asyncio.create_subprocess_exec", side_effect=mock_gen
    )
    return AioSubproc(create_subprocess, Process)


@pytest.fixture(scope="function")
def push_tuples():
    paths = (
        os.path.join(*dirs)
        for dirs in [
            ("some", "awesome", "path"),
            ("other", "path"),
            ("final",),
        ]
    )
    urls = (
        "https://slarse.se/best-repo.git",
        "https://completely-imaginary-repo-url.com/repo.git",
        "https://somerepourl.git",
    )
    branches = ("master", "other", "development-branch")
    tups = [
        git.Push(local_path=path, repo_url=url, branch=branch)
        for path, url, branch in zip(paths, urls, branches)
    ]
    return tups


def test_clone_single_raises_on_non_zero_exit_from_git_pull(env_setup, mocker):
    stderr = b"This is pretty bad!"
    # already patched in env_setup fixture
    subprocess.run.return_value = RunTuple(1, "", stderr)

    with pytest.raises(exception.CloneFailedError) as exc:
        git.clone_single(f"{URL_TEMPLATE.format('')}")
    assert "Failed to clone" in str(exc.value)


def test_clone_single_issues_correct_command_with_defaults(env_setup):
    expected_command = (
        f"git clone --single-branch {env_setup.expected_url}".split()
    )

    git.clone_single(URL_TEMPLATE.format(""))
    subprocess.run.assert_any_call(
        expected_command,
        cwd=".",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def test_clone_single_issues_correct_command_non_default_branch(env_setup):
    branch = "other-branch"
    expected_command = (
        f"git clone --single-branch {env_setup.expected_url} {branch}".split()
    )

    git.clone_single(URL_TEMPLATE.format(""), branch=branch)

    subprocess.run.assert_any_call(
        expected_command,
        cwd=".",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def test_clone_single_issues_correct_command_with_cwd(env_setup):
    working_dir = "some/working/dir"
    branch = "other-branch"
    expected_command = (
        f"git clone --single-branch {env_setup.expected_url} {branch}".split()
    )

    git.clone_single(URL_TEMPLATE.format(""), branch=branch, cwd=working_dir)
    subprocess.run.assert_called_once_with(
        expected_command,
        cwd=str(working_dir),
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


class TestPush:
    """Tests for push."""

    @pytest.mark.parametrize("tries", [0, -2, -10])
    def test_push_raises_when_tries_is_less_than_one(
        self, env_setup, push_tuples, tries
    ):
        with pytest.raises(ValueError) as exc_info:
            git.push(push_tuples, tries=tries)

        assert "tries must be larger than 0" in str(exc_info.value)

    def test(self, env_setup, push_tuples, aio_subproc):
        """Test that push works as expected when no exceptions are thrown by
        tasks.
        """
        expected_calls = [
            call(
                *f"git push {url} {branch}".split(),
                cwd=os.path.abspath(local_repo),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for local_repo, url, branch in push_tuples
        ]

        successful_pts, failed_pts = git.push(push_tuples)

        assert not failed_pts
        assert successful_pts == push_tuples
        aio_subproc.create_subprocess.assert_has_calls(expected_calls)

    def test_tries_all_calls_despite_exceptions(
        self, env_setup, push_tuples, mocker
    ):
        """Test that push tries to push all push tuple values even if there
        are exceptions.
        """
        tries = 3
        expected_calls = [
            call(pt) for pt in sorted(push_tuples, key=lambda pt: pt.repo_url)
        ] * tries

        async def raise_(pt):
            raise exception.PushFailedError(
                "Push failed", 128, b"some error", pt.repo_url
            )

        mocker.patch("_repobee.git._push_async", side_effect=raise_)

        successful_pts, failed_pts = git.push(push_tuples, tries=tries)

        assert not successful_pts
        assert failed_pts == push_tuples
        git._push_async.assert_has_calls(expected_calls, any_order=True)

    def test_stops_retrying_when_failed_pushes_succeed(
        self, env_setup, push_tuples, mocker
    ):
        tried = False
        fail_pt = push_tuples[1]

        async def raise_once(pt):
            nonlocal tried
            if not tried and pt == fail_pt:
                tried = True
                raise exception.PushFailedError(
                    "Push failed", 128, b"some error", pt.repo_url
                )

        expected_num_calls = len(push_tuples) + 1  # one retry

        async def raise_(pt):
            raise exception.PushFailedError(
                "Push failed", 128, b"some error", pt.repo_url
            )

        async_push_mock = mocker.patch(
            "_repobee.git._push_async", side_effect=raise_once
        )

        git.push(push_tuples, tries=10)

        assert len(async_push_mock.call_args_list) == expected_num_calls

    def test_tries_all_calls_when_repos_up_to_date(
        self, env_setup, push_tuples, aio_subproc
    ):
        aio_subproc.process.stderr = b"Everything up-to-date"

        expected_calls = [
            call(
                *f"git push {pt.repo_url}".split(),
                pt.branch,
                cwd=os.path.abspath(pt.local_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for pt in push_tuples
        ]

        git.push(push_tuples)

        aio_subproc.create_subprocess.assert_has_calls(expected_calls)


class TestClone:
    """Tests for clone."""

    _WORKING_DIR = pathlib.Path("some/working/dir")

    @pytest.fixture
    def specs(self, push_tuples):
        return [
            git.CloneSpec(
                repo_url=pt.repo_url,
                dest=self._WORKING_DIR / util.repo_name(pt.repo_url),
            )
            for pt in push_tuples
        ]

    def test_happy_path(self, env_setup, push_tuples, specs, aio_subproc):
        expected_subproc_calls = [
            call(
                *f"git pull {spec.repo_url}".split(),
                cwd=str(spec.dest),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for spec in specs
        ]

        failed_specs = git.clone(specs)

        assert not failed_specs
        aio_subproc.create_subprocess.assert_has_calls(expected_subproc_calls)

    def test_tries_all_calls_despite_exceptions(
        self, env_setup, push_tuples, specs, mocker
    ):
        fail_specs = [specs[0], specs[-1]]

        expected_calls = [call(spec) for spec in specs]

        async def raise_(spec, *args, **kwargs):
            if spec in fail_specs:
                raise exception.CloneFailedError(
                    "Some error",
                    returncode=128,
                    stderr=b"Something",
                    clone_spec=spec,
                )

        clone_mock = mocker.patch(
            "_repobee.git._clone_async", autospec=True, side_effect=raise_
        )

        failed_specs = git.clone(specs)

        assert failed_specs == fail_specs
        clone_mock.assert_has_calls(expected_calls)

    def test_tries_all_calls_despite_exceptions_lower_level(
        self, env_setup, push_tuples, mocker, non_zero_aio_subproc, specs
    ):
        """Same test as test_tries_all_calls_desipite_exception, but
        asyncio.create_subprocess_exec is mocked out instead of
        git._clone_async
        """
        expected_calls = [
            call(
                *f"git pull {spec.repo_url}".split(),
                cwd=str(spec.dest),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for spec in specs
        ]

        failed_specs = git.clone(specs)
        non_zero_aio_subproc.create_subprocess.assert_has_calls(expected_calls)

        assert failed_specs == specs
