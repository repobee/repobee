import itertools
import sys
import tempfile
from contextlib import contextmanager

import pytest

from _repobee import fileutil


@pytest.fixture
def directory_structure(tmpdir):
    """Create a directory structure like this:


                   root
                _____|___________________
                |    |           |       |
              repo Main.java  epic.py  other_repo
        ________|________          ______|_________
        |       |       |          |     |        |
    README.md test.py best.py    Main.java test.py epic.py
    """
    root_files = ["Main.java", "epic.py"]
    repo_files = ["README.md", "test.py", "best.py"]
    other_repo_files = ["Main.java", "test.py", "epic.py"]

    repo = tmpdir.mkdir("repo")
    other_repo = tmpdir.mkdir("other_repo")

    for dir_, filenames in [
        (tmpdir, root_files),
        (repo, repo_files),
        (other_repo, other_repo_files),
    ]:
        for filename in filenames:
            file = dir_.join(filename)
            file.ensure()

    java_files = [
        str(f)
        for f in (tmpdir.join("Main.java"), other_repo.join("Main.java"))
    ]
    python_files = [
        str(f)
        for f in (
            tmpdir.join("epic.py"),
            repo.join("test.py"),
            repo.join("best.py"),
            other_repo.join("test.py"),
            other_repo.join("epic.py"),
        )
    ]
    readme_files = [str(repo.join("README.md"))]

    return tmpdir, java_files, python_files, readme_files


class TestFindFilesByExtension:
    """Tests for find_files_by_extension."""

    def test_find_java_files(self, directory_structure):
        root, java_files, *_ = directory_structure

        files = list(fileutil.find_files_by_extension(str(root), ".java"))

        filepaths = [str(file.resolve()) for file in files]

        assert sorted(filepaths) == sorted(java_files)

    def test_find_python_files(self, directory_structure):
        root, _, python_files, *r = directory_structure

        files = list(fileutil.find_files_by_extension(str(root), ".py"))

        filepaths = [str(file.resolve()) for file in files]

        assert sorted(filepaths) == sorted(python_files)

    def test_find_java_py_md_files(self, directory_structure):
        """Try to find all three types at the same time."""
        root, java_files, python_files, md_files = directory_structure
        expected_files = list(
            itertools.chain(java_files, python_files, md_files)
        )

        files = list(
            fileutil.find_files_by_extension(str(root), ".java", ".py", ".md")
        )

        filepaths = [str(file.resolve()) for file in files]

        assert sorted(filepaths) == sorted(expected_files)

    def test_works_when_no_files_found(self, directory_structure):
        root, *_ = directory_structure

        files = list(
            fileutil.find_files_by_extension(str(root), ".doesnotexist")
        )

        assert not files

    def test_does_not_find_files_when_dot_is_omitted(
        self, directory_structure
    ):
        root, *_ = directory_structure

        files = list(fileutil.find_files_by_extension(str(root), "java"))

        assert not files

    def test_throws_exception_when_no_extension_is_provided(
        self, directory_structure
    ):
        root, *_ = directory_structure
        with pytest.raises(ValueError):
            list(fileutil.find_files_by_extension(str(root)))


@contextmanager
def written_tmpfile(text):
    """Create a context within which there is a temporary file with some text
    in it. The file is deleted after the context exits. Yields the temporary
    file.

    Args:
        text: Text to put in the temporary file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(
            dir=tmpdir,
            mode="w",
            encoding=sys.getdefaultencoding(),
            delete=False,
        ) as file:
            file.write(text)
            file.flush()
        yield file


class TestReadIssueFromFile:
    """Tests for the read_issue_from_file function."""

    def test_raises_when_file_does_not_exist(self):
        # temp file is deleted when closed
        with tempfile.NamedTemporaryFile() as file:
            filepath = file.name
        with pytest.raises(ValueError) as exc_info:
            fileutil.read_issue_from_file(filepath)
        assert "is not a file" in str(exc_info.value)

    def test_raises_when_path_points_to_dir(self):
        """Should raise if the path points to a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                fileutil.read_issue_from_file(tmpdir)
            assert "is not a file" in str(exc_info.value)

    def test_empty_title_and_body_if_file_is_empty(self):
        """It's not an error to specify an empty file, should result in empty
        title and empty body.
        """
        with written_tmpfile("") as file:
            issue = fileutil.read_issue_from_file(file.name)
        assert issue.title == ""
        assert issue.body == ""

    def test_only_title(self):
        """Title should be as specified and body should be empty."""
        expected_title = "This is the title"
        with written_tmpfile(expected_title) as file:
            issue = fileutil.read_issue_from_file(file.name)
        assert issue.title == expected_title
        assert issue.body == ""

    def test_title_and_body(self):
        """If there is a line separator in the file, there should be both title
        and body.
        """
        expected_title = "This is the title again"
        expected_body = "Body **with formatting** and\nmultiple\nlines"
        text = "\n".join([expected_title, expected_body])

        with written_tmpfile(text) as file:
            issue = fileutil.read_issue_from_file(file.name)

        assert issue.title == expected_title
        assert issue.body == expected_body
