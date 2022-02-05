import time

import pytest
import requests
import responses

from _repobee import rate_limit


_ARBITRARY_NUMBER = 1


class TestRateLimitModifyRequests:
    """Tests for the rate_limit_modify_requests function."""

    def test_replaces_requests_modify_functions(self):
        original_functions = _get_requests_modify_functions()

        rate_limit.rate_limit_modify_requests(_ARBITRARY_NUMBER)

        functions_after_rate_limiting = _get_requests_modify_functions()

        assert original_functions != functions_after_rate_limiting

    @responses.activate
    @pytest.mark.parametrize(
        "method_name", rate_limit.MODIFY_REQUEST_METHOD_NAMES
    )
    def test_rate_limits_modify_requests(self, method_name):
        url = "https://repobee.org"

        responses.add(
            getattr(responses, method_name.upper()),
            url,
            json={"yay": "yay"},
            status=200,
        )

        rate_limit_in_seconds = 0.5
        rate_limit.rate_limit_modify_requests(rate_limit_in_seconds)

        time_before = time.time()

        request_function = getattr(requests, method_name)
        request_function(url)
        request_function(url)

        elapsed_time = time.time() - time_before
        assert elapsed_time > rate_limit_in_seconds


class TestRemoveRateLimits:
    """Tests for the remove_rate_limits function."""

    def test_restores_original_functions(self):
        original_functions = _get_requests_modify_functions()
        rate_limit.rate_limit_modify_requests(_ARBITRARY_NUMBER)

        assert (
            original_functions != _get_requests_modify_functions()
        ), "requests modify functions were not replaced, test setup invalid"

        rate_limit.remove_rate_limits()

        functions_after_rate_limit_removal = _get_requests_modify_functions()

        assert functions_after_rate_limit_removal == original_functions


@pytest.fixture(autouse=True)
def remove_rate_limits():
    rate_limit.remove_rate_limits()


def _get_requests_modify_functions():
    return {
        getattr(requests, name)
        for name in rate_limit.MODIFY_REQUEST_METHOD_NAMES + ("request",)
    }
