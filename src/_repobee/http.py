import time
import functools

import requests

import repobee_plug as plug

MODIFY_REQUEST_METHOD_NAMES = ("post", "put", "patch", "delete")

_ORIGINAL_REQUESTS_METHODS = {
    method_name: getattr(requests, method_name)
    for method_name in MODIFY_REQUEST_METHOD_NAMES + ("request",)
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

        original_request_method(method, url, *args, **kwargs)

    requests.request = request
    requests.put = functools.partial(request, "put")
    requests.patch = functools.partial(request, "patch")
    requests.delete = functools.partial(request, "delete")
    requests.post = functools.partial(request, "post")


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
        return requests.get(test_url) is not None
    except requests.exceptions.ConnectionError:
        return False
