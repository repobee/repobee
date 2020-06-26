import pytest

import repobee_plug as plug
from repobee_plug import _deprecation


def test_cant_deprecate_non_hook_function():
    def func():
        pass

    with pytest.raises(plug.PlugError) as exc_info:
        _deprecation.deprecate(remove_by_version="3.0.0")(func)

    assert "can't deprecate non-hook function" in str(exc_info.value)
    assert "func={}".format(func) in str(exc_info.value)
    assert exc_info.value.kwargs["func"] == func
