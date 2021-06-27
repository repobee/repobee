import pytest
from repobee_plug import platform
from repobee_plug import exceptions

import collections
import datetime

from typing import Optional, List


def api_methods():
    methods = platform.methods(platform._APISpec.__dict__)
    assert methods, "there must be api methods"
    return methods.items()


def api_method_ids():
    methods = platform.methods(platform._APISpec.__dict__)
    return list(methods.keys())


class TestAPI:
    @pytest.mark.parametrize("method", api_methods(), ids=api_method_ids())
    def test_raises_when_unimplemented_method_called(self, method):
        """Test that get_teams method raises NotImplementedError when called if
        left undefined.
        """

        class API(platform.PlatformAPI):
            pass

        name, impl = method
        params = platform.parameters(impl)

        with pytest.raises(NotImplementedError):
            m = getattr(API, name)
            arguments = (None,) * len(params)
            m(*arguments)

    def test_raises_when_method_incorrectly_declared(self):
        """``get_teams`` takes only a self argument, so defining it with a
        different argument should raise.
        """

        with pytest.raises(exceptions.APIImplementationError):

            class API(platform.PlatformAPI):
                def get_teams(a):
                    pass

    def test_accepts_init_with_strict_subset_of_args(self):
        """Test that ``__init__`` can be defined with a strict subset of the
        args in _APISpec.__init__.
        """

        class API(platform.PlatformAPI):
            def __init__(self, base_url):
                pass

        api = API("some-url")
        assert isinstance(api, platform.PlatformAPI)

    def test_raises_when_init_has_superset_of_args(self):
        """Test that ``__init__`` cannot be defined with a superset of the args
        in _APISpec.__init__.
        """

        with pytest.raises(exceptions.APIImplementationError) as exc_info:

            class API(platform.PlatformAPI):
                def __init__(self, base_url, token, org_name, user, other):
                    pass

        assert "other" in str(exc_info.value)

    def test_accepts_correctly_defined_method(self):
        """API should accept a correctly defined method, and not alter it in any
        way.
        """
        expected = 42

        class API(platform.PlatformAPI):
            def __init__(self, base_url, token, org_name, user):
                pass

            def get_teams(self, team_names: Optional[List[str]] = None):
                return expected

        assert API(None, None, None, None).get_teams() == expected

    def test_raises_when_method_has_incorrect_default_arg(self):
        with pytest.raises(exceptions.APIImplementationError):

            class API(platform.PlatformAPI):
                def __init__(self, base_url, token, org_name, user):
                    pass

                def get_teams(self, team_names="hello"):
                    pass


class TestAPIObject:
    def test_raises_when_accessing_none_implementation(self):
        """Any APIObject should raise when the implementation attribute is
        accessed, if it is None.
        """

        class APIObj(
            platform.APIObject,
            collections.namedtuple("APIObj", "implementation"),
        ):
            def __new__(cls):
                return super().__new__(cls, implementation=None)

        obj = APIObj()

        with pytest.raises(AttributeError) as exc_info:
            obj.implementation

        assert "invalid access to 'implementation': not initialized" in str(
            exc_info.value
        )

    def test_does_not_raise_when_accessing_initialized_implementation(self):
        """If implementation is not None, there should be no error on access"""
        implementation = 42

        class APIObj(
            platform.APIObject,
            collections.namedtuple("APIObj", "implementation"),
        ):
            def __new__(cls):
                return super().__new__(cls, implementation=implementation)

        obj = APIObj()

        assert obj.implementation == implementation


class TestIssue:
    def test_lossless_to_dict_from_dict_roundtrip(self):
        """Test that running to_dict and then from_dict on the resulting
        dict results in the original Issue instance, minus the implementation
        field (which should always be None in a reconstructed instance).
        """
        issue = platform.Issue(
            title="Some title",
            body="Some body",
            number=3,
            created_at=str(datetime.datetime(2019, 8, 16, 8, 57, 23, 949179)),
            author="slarse",
            implementation=None,
        )

        asdict = issue.to_dict()
        reconstructed = platform.Issue.from_dict(asdict)

        assert reconstructed == issue


class TestTeam:
    """Tests for the Team class."""

    def test_lowercases_usernames(self):
        """While all of the platforms currently supported are case insensitive,
        some still allow usernames to contain e.g. capital letters. We don't
        want this to appear in RepoBee, as it can case problems such as those
        reported in https://github.com/repobee/repobee/issues/900.
        """
        usernames = ["siMon", "ALICE", "eVe"]
        lowercase_usernames = ["simon", "alice", "eve"]

        team = platform.Team(
            members=usernames, name="yep", id=1, implementation="fake"
        )

        assert team.members == lowercase_usernames


class TestRepo:
    """Tests for Repo class"""

    def test_lowercase_name(self):
        name = "TeStREpo"
        name_lowercase = "testrepo"

        repo = platform.Repo(
            name=name,
            description="descr",
            private=False,
            url="https://sample.com",
            implementation="fake",
        )
        assert repo.name == name_lowercase
