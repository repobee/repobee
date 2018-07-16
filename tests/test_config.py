import pytest
from gits_pet import config
from gits_pet import exception

STUDENTS = pytest.constants.STUDENTS
USER = pytest.constants.USER
GITHUB_BASE_URL = pytest.constants.GITHUB_BASE_URL
ORG_NAME = pytest.constants.ORG_NAME


class TestGetConfiguredDefaults:
    """Tests for get_configured_defaults"""

    def test_get_configured_defaults_no_config_file(self, isfile_mock):
        defaults = config.get_configured_defaults()
        assert not defaults

    def test_get_configured_defaults_empty_file(self, empty_config_mock):
        with pytest.raises(exception.FileError) as exc_info:
            defaults = config.get_configured_defaults()
        assert "does not contain the required [DEFAULTS] header" in str(
            exc_info)

    def test_get_configured_defaults_reads_full_config(self, config_mock, students_file):
        defaults = config.get_configured_defaults()
        assert defaults['user'] == USER
        assert defaults['github_base_url'] == GITHUB_BASE_URL
        assert defaults['org_name'] == ORG_NAME
        assert defaults['students_file'] == students_file.name
