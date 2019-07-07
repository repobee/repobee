"""Module for constants used throughout the test suite."""
import string
import collections
from datetime import datetime
from itertools import permutations

from repobee import apimeta

USER = "slarse"
ORG_NAME = "test-org"
MASTER_ORG_NAME = "test-master-org"
HOST_URL = "https://some_enterprise_host"
BASE_URL = "{}/api/v3".format(HOST_URL)

# 5! = 120 different students
STUDENTS = tuple(
    apimeta.Team(members=["".join(perm)])
    for perm in permutations(string.ascii_lowercase[:5])
)
ISSUE_PATH = "some/issue/path"
ISSUE = apimeta.Issue(
    title="Best title", body="This is the body of the issue."
)
PLUGINS = ["javac", "pylint"]
TOKEN = "besttoken1337"
CONFIG_TOKEN = "bestconfigtoken"
FIXED_DATETIME = datetime(2009, 11, 22)


User = collections.namedtuple("User", ("login",))
