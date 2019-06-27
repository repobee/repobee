import pytest
from repobee import formatters
from repobee import tuples


def strs_to_reviews(*repo_names, done=True):
    return [tuples.Review(repo, done) for repo in repo_names]


@pytest.fixture
def students():
    return ["ham", "spam", "bacon", "eggs"]


class TestPeerReviewFormatter:
    """Tests for format_peer_review_progress_output"""

    def test_all_reviews_done(self, students):
        num_reviews = 2
        reviews = {
            "ham": strs_to_reviews("spam-week-1", "bacon-week-1"),
            "spam": strs_to_reviews("bacon-week-1", "eggs-week-1"),
            "bacon": strs_to_reviews("eggs-week-1", "ham-week-1"),
            "eggs": strs_to_reviews("ham-week-1", "spam-week-1"),
        }

        expected_output = """
Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews
[0mreviewer        num done        num remaining   repos remaining 
[48;5;22m[38;5;15mham             2               0                               [0m
[48;5;22m[38;5;15mspam            2               0                               [0m
[48;5;22m[38;5;15mbacon           2               0                               [0m
[48;5;22m[38;5;15meggs            2               0                               [0m
"""  # noqa: E501,W291

        actual_output = formatters.format_peer_review_progress_output(
            reviews, students, num_reviews
        )

        assert actual_output.strip() == expected_output.strip()

    def test_no_reviews_done(self, students):
        """Test output is correct when correct amount of reviews are assigned,
        but none of them are done.
        """
        num_reviews = 2
        reviews = {
            "ham": strs_to_reviews("spam-week-1", "bacon-week-1", done=False),
            "spam": strs_to_reviews("bacon-week-1", "eggs-week-1", done=False),
            "bacon": strs_to_reviews("eggs-week-1", "ham-week-1", done=False),
            "eggs": strs_to_reviews("ham-week-1", "spam-week-1", done=False),
        }

        expected_output = """
Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews
[0mreviewer        num done        num remaining   repos remaining 
[48;5;239m[38;5;15mham             0               2               spam-week-1,bacon-week-1[0m
[48;5;235m[38;5;15mspam            0               2               bacon-week-1,eggs-week-1[0m
[48;5;239m[38;5;15mbacon           0               2               eggs-week-1,ham-week-1[0m
[48;5;235m[38;5;15meggs            0               2               ham-week-1,spam-week-1[0m
"""  # noqa: E501,W291

        actual_output = formatters.format_peer_review_progress_output(
            reviews, students, num_reviews
        )
        assert actual_output.strip() == expected_output.strip()

    def test_student_with_too_few_assigned_reviews(self, students):
        """Test that the single student (bacon in this case) is highlighted
        with red.
        """
        num_reviews = 2
        reviews = {
            "ham": strs_to_reviews("spam-week-1", "bacon-week-1"),
            "spam": strs_to_reviews("bacon-week-1", "eggs-week-1"),
            "bacon": strs_to_reviews("eggs-week-1"),
            "eggs": strs_to_reviews("ham-week-1", "spam-week-1"),
        }
        expected_output = """
Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews
[0mreviewer        num done        num remaining   repos remaining 
[48;5;22m[38;5;15mham             2               0                               [0m
[48;5;22m[38;5;15mspam            2               0                               [0m
[48;5;1m[38;5;15mbacon           1               0                               [0m
[48;5;22m[38;5;15meggs            2               0                               [0m
"""  # noqa: E501,W291
        actual_output = formatters.format_peer_review_progress_output(
            reviews, students, num_reviews
        )
        assert actual_output.strip() == expected_output.strip()

    def test_mixed(self, students):
        """One student is done, one has performed half, one has too few
        assigned, one has more.
        """
        num_reviews = 2
        reviews = {
            "ham": strs_to_reviews("spam-week-1", "bacon-week-1", done=False),
            "spam": [
                tuples.Review("bacon-week-1", False),
                tuples.Review("eggs-week-1", False),
            ],
            "bacon": strs_to_reviews("eggs-week-1", done=False),
            "eggs": strs_to_reviews(
                "ham-week-1", "spam-week-1", "bacon-week-1", done=True
            ),
        }
        expected_output = """
Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews
[0mreviewer        num done        num remaining   repos remaining 
[48;5;239m[38;5;15mham             0               2               spam-week-1,bacon-week-1[0m
[48;5;235m[38;5;15mspam            0               2               bacon-week-1,eggs-week-1[0m
[48;5;1m[38;5;15mbacon           0               1               eggs-week-1     [0m
[48;5;1m[38;5;15meggs            3               0                               [0m
"""  # noqa: E501,W291
        actual_output = formatters.format_peer_review_progress_output(
            reviews, students, num_reviews
        )
        assert actual_output.strip() == expected_output.strip()

    def test_empty(self):
        """No students, no reviews"""
        students = []
        reviews = {}
        num_reviews = 0
        expected_output = """
Color coding: grey: not done, green: done, red: num done + num remaining != num_reviews
[0mreviewer        num done        num remaining   repos remaining 
"""  # noqa: E501,W291
        actual_output = formatters.format_peer_review_progress_output(
            reviews, students, num_reviews
        )
        assert actual_output.strip() == expected_output.strip()
