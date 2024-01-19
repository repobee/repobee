import requests

DEFAULT_INTERNET_CONNECTION_CHECK_URL = "https://repobee.org"


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
