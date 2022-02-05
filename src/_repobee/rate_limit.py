import requests
import time
import functools

MODIFY_REQUEST_METHOD_NAMES = ("post", "put", "patch", "delete")

_ORIGINAL_REQUESTS_METHODS = {
    method_name: getattr(requests, method_name)
    for method_name in MODIFY_REQUEST_METHOD_NAMES + ("request",)
}


def rate_limit_modify_requests(rate_limit_in_seconds: int) -> None:
    """Apply a rate limit to all modifying requests (put, patch, delete, post).

    This is currently necessary at least for GitHub due to the newly introduced
    secondary rate limits, see
    https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits.

    Args:
        rate_limit_in_seconds: Minimum amount of seconds between each modify
            request.
    """
    last_modify_time = 0

    original_request_method = requests.request

    def request(method, *args, **kwargs):
        nonlocal last_modify_time

        if method.lower() in MODIFY_REQUEST_METHOD_NAMES:
            seconds_since_last_modify = time.time() - last_modify_time
            if seconds_since_last_modify < rate_limit_in_seconds:
                time.sleep(rate_limit_in_seconds - seconds_since_last_modify)
            last_modify_time = time.time()

        original_request_method(method, *args, **kwargs)

    requests.request = request
    requests.put = functools.partial(request, "put")
    requests.patch = functools.partial(request, "patch")
    requests.delete = functools.partial(request, "delete")
    requests.post = functools.partial(request, "post")


def remove_rate_limits() -> None:
    """Remove any previously applied rate limits."""
    for method_name, original_method in _ORIGINAL_REQUESTS_METHODS.items():
        setattr(requests, method_name, original_method)
