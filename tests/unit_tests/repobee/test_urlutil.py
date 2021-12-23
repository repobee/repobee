import pytest

from _repobee import urlutil


@pytest.mark.parametrize(
    "url, expected_name",
    [
        ("https://github.com/slarse/some-repo", "some-repo"),
        ("https://github.com/slarse/some-repo.git", "some-repo"),
        ("https://gitrepourls/repos/some-repo/base-name", "base-name"),
        ("https://gitrepourls/repos/some-repo/base-name.git", "base-name"),
    ],
)
def test_repo_name_extracts_correct_part(url, expected_name):
    assert urlutil.extract_repo_name(url) == expected_name
