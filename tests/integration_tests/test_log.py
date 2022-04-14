"""Tests for the logging facilities."""
import pytest

from repobee_testhelpers import funcs


def test_auto_truncates_log_file(monkeypatch, tmp_path_factory):
    """The log file should be truncated by any command when it gets too large."""
    # arrange
    log_dir = tmp_path_factory.mktemp("logs")
    logfile = log_dir / "repobee.log"
    max_size = 1024 * 10

    logfile.write_bytes(b"a\n" * max_size * 10)

    monkeypatch.setattr("_repobee.constants.LOG_DIR", log_dir)
    monkeypatch.setattr("_repobee.constants.MAX_LOGFILE_SIZE", max_size)

    # act
    with pytest.raises(SystemExit):
        funcs.run_repobee("-h")

    # assert
    assert 0 < len(logfile.read_bytes()) < max_size


def test_auto_truncation_retains_final_lines(monkeypatch, tmp_path_factory):
    """The log file should be truncated by any command when it gets too large."""
    # arrange
    log_dir = tmp_path_factory.mktemp("logs")
    logfile = log_dir / "repobee.log"
    max_size = 1024 * 10

    logfile.write_bytes(b"a\n" * max_size * 10)
    last_lines = [b"these are", b"the last lines", b"of the log"]

    with open(logfile, mode="ab") as f:
        for line in last_lines:
            f.write(line)

    monkeypatch.setattr("_repobee.constants.LOG_DIR", log_dir)
    monkeypatch.setattr("_repobee.constants.MAX_LOGFILE_SIZE", max_size)

    # act
    with pytest.raises(SystemExit):
        funcs.run_repobee("-h")

    # assert
    log_contents = logfile.read_bytes()
    for line in last_lines:
        assert line in log_contents
