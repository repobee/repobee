import time
import functools

from typing import Mapping, Optional

import requests

import repobee_plug as plug

MODIFY_REQUEST_METHOD_NAMES = ("post", "put", "patch", "delete")

ALL_REQUEST_METHOD_NAMES = (
    "get",
    "options",
    "head",
    "post",
    "put",
    "patch",
    "delete",
)

_ORIGINAL_REQUESTS_METHODS = {
    method_name: getattr(requests, method_name)
    for method_name in ALL_REQUEST_METHOD_NAMES + ("request",)
}

DEFAULT_INTERNET_CONNECTION_CHECK_URL = "https://repobee.org"


def rate_limit_modify_requests(
    base_url: str, rate_limit_in_seconds: float
) -> None:
    """Apply a rate limit to all modifying requests (put, patch, delete, post)
    going to the given base URL.

    This is currently necessary at least for GitHub due to the newly introduced
    secondary rate limits, see
    https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits.

    Args:
        base_url: Base URL on which to rate limit modify requests.
        rate_limit_in_seconds: Minimum amount of seconds between each modify
            request.
    """
    plug.log.debug(
        f"Rate limiting modify requests to {1 / rate_limit_in_seconds} "
        "requests per second"
    )
    last_modify_time = 0

    original_request_method = requests.request

    def request(method, url, *args, **kwargs):
        nonlocal last_modify_time

        if (
            url.casefold().startswith(base_url.casefold())
            and method.lower() in MODIFY_REQUEST_METHOD_NAMES
        ):
            seconds_since_last_modify = time.time() - last_modify_time
            if seconds_since_last_modify < rate_limit_in_seconds:
                time.sleep(rate_limit_in_seconds - seconds_since_last_modify)
            last_modify_time = time.time()

        # pylint: disable=missing-timeout
        original_request_method(method, url, *args, **kwargs)

    requests.request = request
    requests.put = functools.partial(request, "put")
    requests.patch = functools.partial(request, "patch")
    requests.delete = functools.partial(request, "delete")
    requests.post = functools.partial(request, "post")


def install_retry_after_handler() -> None:
    """Install a handler that interposes itself into HTTP requests and honors the
    Retry-After header by sleeping for the desired amount of time.
    """
    plug.log.debug("Installing Retry-After handler")
    original_request_method = requests.request

    def request_with_retry_after_handling(method, url, *args, **kwargs):
        # pylint: disable=missing-timeout
        response = original_request_method(method, url, *args, **kwargs)
        retry_after_raw = _get_value_case_insensitive(
            "retry-after", response.headers
        )
        if not retry_after_raw:
            return response

        plug.log.warning(
            f"Rate limited on request to {url}, retrying after {retry_after_raw}s"
        )

        retry_after = float(retry_after_raw)
        time.sleep(retry_after)
        return request_with_retry_after_handling(method, url, *args, **kwargs)

    for method_name in ALL_REQUEST_METHOD_NAMES:
        retry_aware_method = functools.partial(
            request_with_retry_after_handling, method_name
        )
        setattr(requests, method_name, retry_aware_method)

    requests.request = request_with_retry_after_handling


def _get_value_case_insensitive(
    search_key: str, mapping: Mapping[str, str]
) -> Optional[str]:
    normalized_mapping = {
        key.casefold(): value for key, value in mapping.items()
    }
    return normalized_mapping.get(search_key.casefold())


def remove_rate_limits() -> None:
    """Remove any previously applied rate limits."""
    plug.log.debug("Removing rate limits")

    for method_name, original_method in _ORIGINAL_REQUESTS_METHODS.items():
        setattr(requests, method_name, original_method)


def is_internet_connection_available(
    test_url=DEFAULT_INTERNET_CONNECTION_CHECK_URL,
) -> bool:
    """Test if an internet connection is available.

    Args:
        test_url: A URL to try to GET.
    """
    try:
        return requests.get(test_url, timeout=10) is not None
    except requests.exceptions.ConnectionError:
        return False
