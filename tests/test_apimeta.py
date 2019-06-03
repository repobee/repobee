import pytest
from repobee import apimeta
from repobee import exception


def api_methods():
    methods = apimeta.methods(apimeta.APISpec.__dict__)
    assert methods, "there must be api methods"
    return methods.items()


def api_method_ids():
    methods = apimeta.methods(apimeta.APISpec.__dict__)
    return list(methods.keys())


@pytest.mark.parametrize("method", api_methods(), ids=api_method_ids())
def test_raises_when_unimplemented_method_called(method):
    """Test that get_teams method raises NotImplementedError when called if
    left undefined.
    """

    class API(apimeta.API):
        pass

    name, impl = method
    params = apimeta.parameter_names(impl)

    with pytest.raises(NotImplementedError):
        m = getattr(API, name)
        arguments = (None,) * len(params)
        m(*arguments)


def test_raises_when_method_incorrectly_declared():
    """``get_teams`` takes only a self argument, so defining it with a
    different argument should raise.
    """

    with pytest.raises(exception.APIImplementationError):

        class API(apimeta.API):
            def get_teams(a):
                pass


def test_accepts_correctly_defined_method():
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
