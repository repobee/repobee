import pytest
from repobee import apimeta
from repobee import exception

import collections


def api_methods():
    methods = apimeta.methods(apimeta.APISpec.__dict__)
    assert methods, "there must be api methods"
    return methods.items()


def api_method_ids():
    methods = apimeta.methods(apimeta.APISpec.__dict__)
    return list(methods.keys())


class TestAPI:
    @pytest.mark.parametrize("method", api_methods(), ids=api_method_ids())
    def test_raises_when_unimplemented_method_called(self, method):
        """Test that get_teams method raises NotImplementedError when called if
        left undefined.
        """

        class API(apimeta.API):
            pass

        name, impl = method
        params = apimeta.parameters(impl)

        with pytest.raises(NotImplementedError):
            m = getattr(API, name)
            arguments = (None,) * len(params)
            m(*arguments)

    def test_raises_when_method_incorrectly_declared(self):
        """``get_teams`` takes only a self argument, so defining it with a
        different argument should raise.
        """

        with pytest.raises(exception.APIImplementationError):

            class API(apimeta.API):
                def get_teams(a):
                    pass

    def test_accepts_correctly_defined_method(self):
        """API should accept a correctly defined method, and not alter it in any
        way.
        """
        expected = 42

        class API(apimeta.API):
            def __init__(self, base_url, token, org_name, user):
                pass

            def get_teams(self):
                return expected

        assert API(None, None, None, None).get_teams() == expected

    def test_raises_when_method_has_incorrect_default_arg(self):
        with pytest.raises(exception.APIImplementationError):

            class API(apimeta.API):
                def __init__(self, base_url, token, org_name, user):
                    pass

                def ensure_teams_and_members(self, teams, permission="push"):
                    pass

    def test_accepts_correct_default_arg(self):
        expected = 42

        class API(apimeta.API):
            def __init__(self, base_url, token, org_name, user):
                pass

            def ensure_teams_and_members(
                self, teams, permission=apimeta.TeamPermission.PUSH
            ):
                return expected

        assert (
            API(None, None, None, None).ensure_teams_and_members(None, None)
            == expected
        )


class TestAPIObject:
    def test_raises_when_accessing_none_implementation(self):
        """Any APIObject should raise when the implementation attribute is
        accessed, if it is None.
        """

        class APIObj(
            apimeta.APIObject,
            collections.namedtuple("APIObj", "implementation"),
        ):
            def __new__(cls):
                return super().__new__(cls, implementation=None)

        obj = APIObj()

        with pytest.raises(AttributeError) as exc_info:
            obj.implementation

        assert "invalid access to 'implementation': not initialized" in str(
            exc_info
        )

    def test_does_not_raise_when_accessing_initialized_implementation(self):
        """If implementation is not None, there should be no error on access"""
        implementation = 42

        class APIObj(
            apimeta.APIObject,
            collections.namedtuple("APIObj", "implementation"),
        ):
            def __new__(cls):
                return super().__new__(cls, implementation=implementation)

        obj = APIObj()

        assert obj.implementation == implementation
