import string
import sys
import os
import collections
import builtins  # noqa: F401
import configparser
from unittest.mock import patch

import pytest

import _repobee.constants
from _repobee.ext.defaults import configwizard


@pytest.fixture
def defaults_options():
    return collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            _repobee.constants.ORDERED_CONFIGURABLE_ARGS,
            string.ascii_lowercase,
        )
    )


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


def test_enters_values_if_config_file_exists_and_user_enters_yes(
    config_mock, defaults_options
):
    """If the config file exists, a prompt should appear, and if the user
    enters yes the wizard should proceed as usuall.
    """
    with patch(
        "builtins.input", side_effect=["yes"] + list(defaults_options.values())
    ):
        configwizard.callback(None, None)

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in defaults_options.items():
        assert confparser[_repobee.constants.repobee_SECTION_HDR][key] == value


def test_enters_values_without_continue_prompt_if_no_config_exists(
    config_mock, defaults_options
):
    """If no config mock can be found (ensured by the nothing_exists fixture),
    then the config wizard chould proceed without prompting for a continue.
    """
    with patch(
        "builtins.input", side_effect=list(defaults_options.values())
    ), patch("pathlib.Path.exists", autospec=True, return_value=False):
        configwizard.callback(None, None)

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in defaults_options.items():
        assert confparser[_repobee.constants.repobee_SECTION_HDR][key] == value


def test_skips_empty_values(empty_config_mock, defaults_options):
    """Test that empty values are not written to the configuration file."""
    defaults_options = collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            _repobee.constants.ORDERED_CONFIGURABLE_ARGS,
            string.ascii_lowercase,
        )
    )
    empty_option = list(defaults_options.keys())[3]
    defaults_options[empty_option] = ""

    with patch(
        "builtins.input", side_effect=list(defaults_options.values())
    ), patch("pathlib.Path.exists", autospec=True, return_value=False):
        configwizard.callback(None, None)

    del defaults_options[empty_option]
    confparser = configparser.ConfigParser()
    confparser.read(str(empty_config_mock))

    assert (
        empty_option not in confparser[_repobee.constants.repobee_SECTION_HDR]
    )
    for key, value in defaults_options.items():
        assert confparser[_repobee.constants.repobee_SECTION_HDR][key] == value


def test_retains_values_that_are_not_specified(config_mock, defaults_options):
    """Test that previous default values are retained if the option is skipped,
    and that plugin sections are not touched.
    """
    # arrange
    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    # add plugin section
    plugin_section = "junit4"
    plugin_options = collections.OrderedDict(
        (option, c)
        for option, c in zip(
            ["hamcrest_path", "junit_path"],
            ["/path/to/hamcrest", "/path/to/junit"],
        )
    )
    confparser.add_section(plugin_section)
    for option, value in plugin_options.items():
        confparser[plugin_section][option] = value
    with open(
        str(config_mock), "w", encoding=sys.getdefaultencoding()
    ) as file:
        confparser.write(file)

    # remove an option and save expected retained value
    empty_option = list(defaults_options.keys())[3]
    defaults_options[empty_option] = ""
    expected_retained_default = confparser[
        _repobee.constants.repobee_SECTION_HDR
    ][empty_option]

    # act
    with patch(
        "builtins.input", side_effect=["yes"] + list(defaults_options.values())
    ):
        configwizard.callback(None, None)

    # assert
    del defaults_options[empty_option]
    parser = configparser.ConfigParser()
    parser.read(str(config_mock))

    assert (
        parser[_repobee.constants.repobee_SECTION_HDR][empty_option]
        == expected_retained_default
    )
    for option, value in defaults_options.items():
        assert parser[_repobee.constants.repobee_SECTION_HDR][option] == value
    for option, value in plugin_options.items():
        assert parser[plugin_section][option] == value


def test_creates_directory(config_mock, tmpdir, defaults_options):
    with patch(
        "builtins.input", side_effect=["yes"] + list(defaults_options.values())
    ), patch("os.makedirs", autospec=True) as makedirs_mock, patch(
        "pathlib.Path.exists", autospec=True, return_value=False
    ):
        configwizard.callback(None, None)

    makedirs_mock.assert_called_once_with(
        os.path.dirname(str(config_mock)), mode=0o700, exist_ok=True
    )
