import pytest
import repobee_plug as plug


class TestMutuallyExclusiveGroup:
    def test_cannot_have_multiple_configurable_options(self):
        with pytest.raises(ValueError) as exc_info:
            plug.cli.mutually_exclusive_group(
                name=plug.cli.option(configurable=True),
                alias=plug.cli.option(configurable=True),
            )

        assert (
            "at most 1 option in a mutex group can be configurable, found 2"
            in str(exc_info.value)
        )
