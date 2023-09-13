import string
import sys
import collections
import builtins  # noqa: F401
import configparser
from unittest.mock import patch

import pytest

import repobee_plug as plug

from _repobee.ext.defaults import configwizard


@pytest.fixture
def defaults_options():
    return collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            get_configurable_default_argnames(),
            string.ascii_lowercase,
        )
    )


def get_configurable_default_argnames():
    default_configurable_args, *_ = plug.manager.hook.get_configurable_args()
    return default_configurable_args.argnames


@pytest.fixture
def select_repobee_section(mocker):
    mocker.patch(
        "bullet.Bullet.launch",
        autospec=True,
        return_value=plug.Config.CORE_SECTION_NAME,
    )


def test_enters_values_if_config_file_exists(
    config_mock, defaults_options, select_repobee_section
):
    """If the config file exists, a prompt should appear, and if the user
    enters yes the wizard should proceed as usual.
    """
    with patch("builtins.input", side_effect=list(defaults_options.values())):
        configwizard.callback(None, plug.Config(config_mock))

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in defaults_options.items():
        assert confparser[plug.Config.CORE_SECTION_NAME][key] == value


def test_enters_values_if_no_config_exists(
    config_mock, defaults_options, select_repobee_section
):
    """If no config mock can be found (ensured by the nothing_exists fixture),
    then the config wizard should proceed without prompting for a continue.
    """
    with patch(
        "builtins.input", side_effect=list(defaults_options.values())
    ), patch("pathlib.Path.exists", autospec=True, return_value=False):
        configwizard.callback(None, plug.Config(config_mock))

    confparser = configparser.ConfigParser()
    confparser.read(str(config_mock))

    for key, value in defaults_options.items():
        assert confparser[plug.Config.CORE_SECTION_NAME][key] == value


def test_skips_empty_values(
    empty_config_mock, defaults_options, select_repobee_section
):
    """Test that empty values are not written to the configuration file."""
    defaults_options = collections.OrderedDict(
        (option, c * 10)
        for option, c in zip(
            get_configurable_default_argnames(),
            string.ascii_lowercase,
        )
    )
    empty_option = list(defaults_options.keys())[3]
    defaults_options[empty_option] = ""

    with patch(
        "builtins.input", side_effect=list(defaults_options.values())
    ), patch("pathlib.Path.exists", autospec=True, return_value=False):
        configwizard.callback(None, plug.Config(empty_config_mock))

    del defaults_options[empty_option]
    confparser = configparser.ConfigParser()
    confparser.read(str(empty_config_mock))

    assert empty_option not in confparser[plug.Config.CORE_SECTION_NAME]
    for key, value in defaults_options.items():
        assert confparser[plug.Config.CORE_SECTION_NAME][key] == value


def test_retains_values_that_are_not_specified(
    config_mock, defaults_options, select_repobee_section
):
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
    expected_retained_default = confparser[plug.Config.CORE_SECTION_NAME][
        empty_option
    ]

    # act
    with patch("builtins.input", side_effect=list(defaults_options.values())):
        configwizard.callback(None, plug.Config(config_mock))

    # assert
    del defaults_options[empty_option]
    parser = configparser.ConfigParser()
    parser.read(str(config_mock))

    assert (
        parser[plug.Config.CORE_SECTION_NAME][empty_option]
        == expected_retained_default
    )
    for option, value in defaults_options.items():
        assert parser[plug.Config.CORE_SECTION_NAME][option] == value
    for option, value in plugin_options.items():
        assert parser[plugin_section][option] == value


def test_creates_directory(defaults_options, select_repobee_section, tmp_path):
    config_file = tmp_path / "path" / "to" / "config.ini"

    with patch("builtins.input", side_effect=list(defaults_options.values())):
        configwizard.callback(None, plug.Config(config_file))

    assert config_file.exists()
