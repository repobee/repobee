import responses
import pytest

import repobee_plug as plug

from repobee_testhelpers._internal import constants
from _repobee.ext import gitea


class TestVerifySettings:
    @responses.activate
    def test_raises_on_no_internet_connection(self):
        with pytest.raises(plug.InternetConnectionUnavailable) as exc_info:
            gitea.GiteaAPI.verify_settings(
                user=constants.USER,
                org_name=constants.ORG_NAME,
                base_url=constants.BASE_URL,
                token=constants.TOKEN,
            )

        assert "could not establish an Internet connection" in str(exc_info)
