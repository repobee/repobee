import pytest
import pathlib

from repobee_testhelpers._internal.docker import (
    run_in_docker,
    VOLUME_DST,
    COVERAGE_VOLUME_DST,
)


@pytest.fixture
def tmpdir_volume_arg(tmpdir):
    """Create a temporary directory and return an argument string that
    will mount a docker volume to it.
    """
    yield "-v {}:{}".format(str(tmpdir), VOLUME_DST)


@pytest.fixture(scope="module", autouse=True)
def coverage_volume():
    covdir = pathlib.Path(".").resolve() / ".coverage_files"
    yield "-v {}:{}".format(str(covdir), COVERAGE_VOLUME_DST)
    covfile = covdir / ".coverage"
    print(list(pathlib.Path(".").iterdir()))
    print(list(covdir.iterdir()))
    assert covfile.is_file()


@pytest.fixture(scope="module", autouse=True)
def generate_coverage_report(coverage_volume):
    """Generate a coverage report after all tests have run."""
    yield
    # xml report for Codecov
    run_in_docker(
        "cd {} && coverage xml".format(COVERAGE_VOLUME_DST),
        extra_args=[coverage_volume],
    )
    # txt report for manual inspection
    run_in_docker(
        "cd {} && coverage report > report.txt".format(COVERAGE_VOLUME_DST),
        extra_args=[coverage_volume],
    )


@pytest.fixture(autouse=True)
def handle_coverage_file(extra_args):
    """Copy the coverage file back and forth."""
    # copy the previous .coverage file into the workdir
    run_in_docker(
        "cp {}/.coverage .".format(COVERAGE_VOLUME_DST), extra_args=extra_args
    )
    yield
    # copy the appended .coverage file into the coverage volume
    run_in_docker(
        "cp .coverage {}".format(COVERAGE_VOLUME_DST), extra_args=extra_args
    )


@pytest.fixture
def extra_args(tmpdir_volume_arg, coverage_volume):
    """Extra arguments to pass to run_in_docker when executing a test."""
    return [tmpdir_volume_arg, coverage_volume]
