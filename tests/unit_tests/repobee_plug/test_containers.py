from repobee_plug import _containers


def test_hook_result_deprecation():
    expected = _containers.Result(
        name="test",
        msg="nothing important",
        status=_containers.Status.WARNING,
        data={"hello": "hello"},
    )

    result = _containers.HookResult(
        hook=expected.name,
        msg=expected.msg,
        status=expected.status,
        data=expected.data,
    )

    assert result == expected
    assert result.hook == result.name
