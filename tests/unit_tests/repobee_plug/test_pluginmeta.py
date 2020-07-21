import argparse
import pathlib

import pytest

import repobee_plug as plug

from repobee_plug import _pluginmeta
from repobee_plug import _exceptions

import repobee


class TestPluginInheritance:
    def test_raises_on_non_hook_public_method(self):
        with pytest.raises(_exceptions.HookNameError) as exc_info:

            class Derived(_pluginmeta.Plugin):
                """Has the hook method config_hook and a non-hook method called
                some_method."""

                def config_hook(self, config_parser):
                    pass

                def some_method(self, x, y):
                    return x + y

        assert "public method(s) with non-hook name" in str(exc_info.value)
        assert "some_method" in str(exc_info.value)
        assert "config_hook" not in str(exc_info.value)

    def test_happy_path(self):
        """Test that a class can be defined when all public methods are have
        hook names.
        """

        class Derived(_pluginmeta.Plugin):
            """Has all hook methods defined."""

            def act_on_cloned_repo(self, path):
                pass

            def clone_parser_hook(self, clone_parser):
                pass

            def parse_args(self, args):
                pass

            def config_hook(self, config_parser):
                pass

            def generate_review_allocations(
                self,
                master_repo_name,
                students,
                num_reviews,
                review_team_name_function,
            ):
                pass

            def get_api_class(self):
                pass

            def api_init_requires(self):
                pass

            def create_extension_command(self):
                pass

    def test_with_private_methods(self):
        """Private methods should be able to have any names."""

        class Derived(_pluginmeta.Plugin):
            """Has all hook methods defined."""

            def act_on_cloned_repo(self, path):
                pass

            def clone_parser_hook(self, clone_parser):
                pass

            def parse_args(self, args):
                pass

            def config_hook(self, config_parser):
                pass

            def generate_review_allocations(
                self,
                master_repo_name,
                students,
                num_reviews,
                review_team_name_function,
            ):
                pass

            def get_api_class(self):
                pass

            def api_init_requires(self):
                pass

            def create_extension_command(self):
                pass

            def _some_method(self, x, y):
                return x + y

            def _other_method(self):
                return self


class TestDeclarativeExtensionCommand:
    """Tests for the declarative style of extension commands."""

    @pytest.fixture
    def basic_greeting_command(self):
        """A basic extension command aimed to test the default values
        of e.g. the command name and description.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.Option(help="your name", required=True)
            age = plug.cli.Option(converter=int, help="your age", default=30)

            def command_callback(self, args, api):
                print(f"My name is {args.name} and I am {args.age} years old")

        return Greeting

    def test_defaults(self, basic_greeting_command):
        """Test declaring an command with no explicit metadata, and checking
        that the defaults are as expected.
        """
        plugin_instance = basic_greeting_command("greeting")
        ext_cmd = plugin_instance.create_extension_command()

        assert callable(ext_cmd.parser)
        assert ext_cmd.name == basic_greeting_command.__name__.lower()
        assert ext_cmd.help == ""
        assert ext_cmd.description == ""
        assert ext_cmd.callback == plugin_instance.command_callback
        assert ext_cmd.requires_api is False
        assert ext_cmd.requires_base_parsers is None
        assert ext_cmd.category is None

    def test_with_metadata(self):
        """Test declaring an command with no explicit metadata, and checking
        that the defaults are as expected.
        """
        expected_category = plug.CoreCommand.config
        expected_name = "cool-greetings"
        expected_help = "This is a greeting command!"
        expected_description = "This is a greeting"
        expected_base_parsers = [
            plug.BaseParser.REPO_NAMES,
            plug.BaseParser.MASTER_ORG,
        ]
        expected_requires_api = True

        class ExtCommand(plug.Plugin, plug.cli.Command):
            __category__ = expected_category
            __action_name__ = expected_name
            __help__ = expected_help
            __description__ = expected_description
            __base_parsers__ = expected_base_parsers
            __requires_api__ = expected_requires_api

            def command_callback(self, args, api):
                pass

        plugin_instance = ExtCommand("greeting")
        ext_cmd = plugin_instance.create_extension_command()

        assert callable(ext_cmd.parser)
        assert ext_cmd.name == expected_name
        assert ext_cmd.help == expected_help
        assert ext_cmd.description == expected_description
        assert ext_cmd.callback == plugin_instance.command_callback
        assert ext_cmd.requires_api == expected_requires_api
        assert ext_cmd.requires_base_parsers == expected_base_parsers

    def test_generated_parser(self, basic_greeting_command):
        """Test the parser that's generated automatically."""
        ext_cmd = basic_greeting_command("greeting").create_extension_command()
        parser = argparse.ArgumentParser()
        ext_cmd.parser(config={}, show_all_opts=True, parser=parser)
        args = parser.parse_args("--name Eve".split())

        assert args.name == "Eve"
        assert args.age == 30  # this is the default for --age

    def test_configuration(self):
        """Test configuring a default value for an option."""

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.Option(
                help="Your name.", required=True, configurable=True
            )

            def command_callback(self, args, api):
                pass

        plugin_name = "greeting"
        configured_name = "Alice"
        config = {plugin_name: {"name": configured_name}}
        ext_cmd = Greeting("greeting").create_extension_command()
        parser = argparse.ArgumentParser()
        ext_cmd.parser(config=config, show_all_opts=False, parser=parser)
        args = parser.parse_args([])

        assert args.name == configured_name

    def test_raises_when_non_configurable_value_is_configured(self):
        """It shouldn't be allowed to have a configuration value for an
        option that is not marked configurable. This is to avoid accidental
        configuration.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.Option(help="Your name.", required=True)

            def command_callback(self, args, api):
                pass

        plugin_name = "greeting"
        configured_name = "Alice"
        config = {plugin_name: {"name": configured_name}}
        ext_cmd = Greeting("greeting").create_extension_command()

        with pytest.raises(plug.PlugError) as exc_info:
            ext_cmd.parser(
                config=config,
                show_all_opts=False,
                parser=argparse.ArgumentParser(),
            )

        assert (
            f"Plugin '{plugin_name}' does not allow 'name' to be configured"
            in str(exc_info.value)
        )

    def test_override_opt_names(self):
        """It should be possible to override both the long and short option
        names of an option.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.Option(
                short_name="-n",
                long_name="--your-name",
                help="your name",
                required=True,
            )

            def command_callback(self, args, api):
                pass

        ext_cmd = Greeting("g").create_extension_command()
        parser = argparse.ArgumentParser()
        ext_cmd.parser(config={}, show_all_opts=False, parser=parser)
        name = "Alice"

        short_opt_args = parser.parse_args(f"-n {name}".split())
        long_opt_args = parser.parse_args(f"--your-name {name}".split())

        assert short_opt_args.name == name
        assert long_opt_args.name == name


class TestDeclarativeCommandExtension:
    """Test creating command extensions to existing commands."""

    @pytest.fixture
    def config_file(self, tmpdir):
        config_file = pathlib.Path(str(tmpdir)) / "config.ini"
        config_file.write_text("[DEFAULTS]")
        return config_file

    def test_add_required_option_to_config_show(
        self, capsys, tmpdir, config_file
    ):
        """Tests adding a required option to ``config show``."""

        class ConfigShowExt(plug.Plugin, plug.cli.CommandExtension):
            __action__ = plug.CoreCommand.config.show

            silly_new_option = plug.cli.Option(help="your name", required=True)

        with pytest.raises(SystemExit):
            repobee.run(
                "config show".split(),
                config_file=config_file,
                plugins=[ConfigShowExt],
            )

        assert (
            "the following arguments are required: --silly-new-option"
            in capsys.readouterr().err
        )

    def test_raises_when_command_and_command_extension_are_subclassed_together(
        self,
    ):
        """It should not be possible for a class to be both a command, and a
        command extension.
        """
        with pytest.raises(plug.PlugError) as exc_info:

            class Ext(
                plug.Plugin, plug.cli.Command, plug.cli.CommandExtension
            ):
                pass

        assert (
            "A plugin cannot be both a Command and a CommandExtension"
            in str(exc_info.value)
        )
