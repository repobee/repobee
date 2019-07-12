import string
import collections
import builtins  # noqa: F401
import configparser
from unittest.mock import patch

import _repobee.constants
from _repobee.ext import configwizard


def test_ext_command_does_not_require_api():
    ext_command = configwizard.create_extension_command()
    assert not ext_command.requires_api


def test_exits_when_config_file_exists_and_user_enters_no(config_mock):
    """If the config file exists, a prompt should appear, and if the user
    enters anything but 'yes' the function should exit and the config file
    should not be altered.
    """
    contents_before = config_mock.read()

    with patch("builtins.input", side_effect=["no"]):
        configwizard.callback(None, None)

    contents_after = config_mock.read()

    assert contents_before == contents_after


def test_enters_values_if_config_file_exists_and_user_enters_yes(config_mock):
    """If the config file exists, a prompt should appear, and if the user
    enters yes the wizard should proceed as usuall.
    """
    expected_options = collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            _repobee.constants.ORDERED_CONFIGURABLE_ARGS,
            string.ascii_lowercase,
        )
    )

    with patch(
        "builtins.input", side_effect=["yes"] + list(expected_options.values())
    ):
        configwizard.callback(None, None)

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in expected_options.items():
        assert (
            confparser[_repobee.constants.DEFAULTS_SECTION_HDR][key] == value
        )


def test_enters_values_without_continue_prompt_if_no_config_exists(
    config_mock
):
    """If no config mock can be found (ensured by the nothing_exists fixture),
    then the config wizard chould proceed without prompting for a continue.
    """
    expected_options = collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            _repobee.constants.ORDERED_CONFIGURABLE_ARGS,
            string.ascii_lowercase,
        )
    )

    config_mock.exists = lambda: False
    with patch("builtins.input", side_effect=list(expected_options.values())):
        configwizard.callback(None, None)

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in expected_options.items():
        assert (
            confparser[_repobee.constants.DEFAULTS_SECTION_HDR][key] == value
        )


def test_skips_empty_values(config_mock):
    """Test that empty values are not written to the configuration file."""
    expected_options = collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            _repobee.constants.ORDERED_CONFIGURABLE_ARGS,
            string.ascii_lowercase,
        )
    )
    empty_option = list(expected_options.values())[3]
    expected_options[empty_option] = ""

    config_mock.exists = lambda: False
    with patch("builtins.input", side_effect=list(expected_options.values())):
        configwizard.callback(None, None)

    del expected_options[empty_option]
    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    assert (
        empty_option not in confparser[_repobee.constants.DEFAULTS_SECTION_HDR]
    )
    for key, value in expected_options.items():
        assert (
            confparser[_repobee.constants.DEFAULTS_SECTION_HDR][key] == value
        )
