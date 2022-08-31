import time
from urllib.parse import urljoin

import pytest
import requests
import responses

from _repobee import http


_ARBITRARY_BASE_URL = "https://repobee.org"
_ARBITRARY_NUMBER = 1


class TestRateLimitModifyRequests:
    """Tests for the rate_limit_modify_requests function."""

    def test_replaces_requests_modify_functions(self):
        original_functions = _get_requests_functions()

        http.rate_limit_modify_requests(_ARBITRARY_BASE_URL, _ARBITRARY_NUMBER)

        functions_after_rate_limiting = _get_requests_functions()

        assert original_functions != functions_after_rate_limiting

    @responses.activate
    @pytest.mark.parametrize("method_name", http.MODIFY_REQUEST_METHOD_NAMES)
    def test_rate_limits_modify_requests(self, method_name):
        url = urljoin(_ARBITRARY_BASE_URL, "/endpoint")

        responses.add(
            getattr(responses, method_name.upper()),
            url,
            status=201,
        )
        responses.add(
            getattr(responses, method_name.upper()),
            url,
            status=201,
        )

        rate_limit_in_seconds = 0.5
        http.rate_limit_modify_requests(
            _ARBITRARY_BASE_URL, rate_limit_in_seconds
        )

        time_before = time.time()

        request_function = getattr(requests, method_name)
        request_function(url)
        request_function(url)

        elapsed_time = time.time() - time_before
        assert elapsed_time > rate_limit_in_seconds

    @responses.activate
    @pytest.mark.parametrize("method_name", http.MODIFY_REQUEST_METHOD_NAMES)
    def test_does_not_rate_limit_non_targeted_url(self, method_name):
        base_url = "https://repobee.org/should_limit"
        other_url = "https://repobee.org/should_not_limit"

        responses.add(
            getattr(responses, method_name.upper()),
            other_url,
            status=201,
        )
        responses.add(
            getattr(responses, method_name.upper()),
            other_url,
            status=201,
        )

        rate_limit_in_seconds = 0.5
        http.rate_limit_modify_requests(base_url, rate_limit_in_seconds)

        time_before = time.time()

        request_function = getattr(requests, method_name)
        request_function(other_url)
        request_function(other_url)

        elapsed_time = time.time() - time_before
        assert elapsed_time < rate_limit_in_seconds


class TestRetryAfterHandler:
    """Tests for the isntall_retry_after_handler function."""

    # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
    @responses.activate(registry=responses.registries.OrderedRegistry)
    @pytest.mark.parametrize("method_name", http.ALL_REQUEST_METHOD_NAMES)
    def test_retries_after_header_time(self, method_name):
        # arrange
        url = urljoin(_ARBITRARY_BASE_URL, "/endpoint")
        retry_after_in_seconds = 0.5

        responses.add(
            getattr(responses, method_name.upper()),
            url,
            status=403,
            adding_headers={"Retry-After": str(retry_after_in_seconds)},
        )
        responses.add(
            getattr(responses, method_name.upper()),
            url,
            status=200,
        )

        http.install_retry_after_handler()

        request_function = getattr(requests, method_name)

        # act
        time_before = time.time()
        response = request_function(url)
        time_after = time.time()

        # assert
        elapsed_time = time_after - time_before
        assert response.status_code == 200
        assert elapsed_time > retry_after_in_seconds


class TestRemoveRateLimits:
    """Tests for the remove_rate_limits function."""

    def test_restores_original_functions(self):
        original_functions = _get_requests_functions()
        http.rate_limit_modify_requests(_ARBITRARY_BASE_URL, _ARBITRARY_NUMBER)
        http.install_retry_after_handler()

        assert (
            original_functions != _get_requests_functions()
        ), "requests modify functions were not replaced, test setup invalid"

        http.remove_rate_limits()

        functions_after_rate_limit_removal = _get_requests_functions()

        assert functions_after_rate_limit_removal == original_functions


@pytest.fixture(autouse=True)
def remove_rate_limits():
    yield
    http.remove_rate_limits()


def _get_requests_functions():
    return {
        getattr(requests, name)
        for name in http.ALL_REQUEST_METHOD_NAMES + ("request",)
    }
