import sys

import pytest
import repobee_plug as plug

from _repobee.ext import studentsyml


def test_raises_PlugError_on_bad_syntax(tmp_path):
    students_file = tmp_path / "students.yml"
    students_file.write_text(
        """
first-team:
    members: [first, second, third
)
""",
        encoding=sys.getdefaultencoding(),
    )

    with pytest.raises(plug.PlugError) as exc_info:
        studentsyml.parse_students_file(students_file)

    assert f"Parse error '{students_file}': Line 2" in str(exc_info.value)


def test_raises_PlugError_on_misspelled_members_mapping(tmp_path):
    students_file = tmp_path / "students.yml"
    students_file.write_text(
        """
first-team:
    members: [first, second]
second-team:
    member: [third]
""",
        encoding=sys.getdefaultencoding(),
    )

    with pytest.raises(plug.PlugError) as exc_info:
        studentsyml.parse_students_file(students_file)

    assert "Missing members mapping for 'second-team'" in str(exc_info.value)
