import pytest
import requests
import responses

import _repobee.http


@pytest.fixture
def add_internet_connection_check_response():
    responses.add(
        responses.GET,
        url=_repobee.http.DEFAULT_INTERNET_CONNECTION_CHECK_URL,
        status=requests.codes.ok,
    )
