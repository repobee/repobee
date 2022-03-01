"""Module for constants used throughout the test suite."""
import string
import collections
from datetime import datetime
from itertools import permutations

import repobee_plug as plug

USER = "slarse"
ORG_NAME = "test-org"
TEMPLATE_ORG_NAME = "test-master-org"
HOST_URL = "https://some_enterprise_host"
BASE_URL = f"{HOST_URL}/api/v3"

# 5! = 120 different students
STUDENTS = tuple(
    plug.StudentTeam(members=["".join(perm)])
    for perm in permutations(string.ascii_lowercase[:5])
)
ISSUE_PATH = "some/issue/path"
ISSUE = plug.Issue(title="Best title", body="This is the body of the issue.")
PLUGINS = ["javac", "pylint"]
TOKEN = "besttoken1337"
CONFIG_TOKEN = "bestconfigtoken"
FIXED_DATETIME = datetime(2009, 11, 22)


User = collections.namedtuple("User", ("login",))
