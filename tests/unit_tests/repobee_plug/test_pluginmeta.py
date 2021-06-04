import argparse
import pathlib

import pytest

import repobee_plug as plug

from repobee_plug import _pluginmeta
from repobee_plug import exceptions

import repobee


@pytest.fixture
def empty_config(tmp_path_factory):
    path = tmp_path_factory.mktemp("dir") / "config.ini"
    return plug.Config(path)


class TestPluginInheritance:
    def test_raises_on_non_hook_public_method(self):
        with pytest.raises(exceptions.HookNameError) as exc_info:

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

            def post_clone(self, repo, api):
                pass

            def clone_parser_hook(self, clone_parser):
                pass

            def handle_parsed_args(self, args):
                pass

            def config_hook(self, config_parser):
                pass

            def generate_review_allocations(
                self,
                assignment_name,
                students,
                num_reviews,
                review_team_name_function,
            ):
                pass

            def get_api_class(self):
                pass

            def api_init_requires(self):
                pass

    def test_with_private_methods(self):
        """Private methods should be able to have any names."""

        class Derived(_pluginmeta.Plugin):
            """Has all hook methods defined."""

            def post_clone(self, repo, api):
                pass

            def clone_parser_hook(self, clone_parser):
                pass

            def handle_parsed_args(self, args):
                pass

            def config_hook(self, config_parser):
                pass

            def generate_review_allocations(
                self,
                assignment_name,
                students,
                num_reviews,
                review_team_name_function,
            ):
                pass

            def get_api_class(self):
                pass

            def api_init_requires(self):
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
            name = plug.cli.option(help="your name", required=True)
            age = plug.cli.option(converter=int, help="your age", default=30)

            def command(self):
                print(f"My name is {self.name} and I am {self.age} years old")

        return Greeting

    def test_default_settings(self, basic_greeting_command, empty_config):
        """Test declaring an command with no explicit metadata, and checking
        that the defaults are as expected.
        """
        plugin_instance = basic_greeting_command("greeting")
        settings = plugin_instance.__settings__

        assert settings.help == ""
        assert settings.description == ""
        assert settings.base_parsers is None
        assert settings.category is None

    def test_generated_parser(self, basic_greeting_command, empty_config):
        """Test the parser that's generated automatically."""
        plugin_instance = basic_greeting_command("g")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=empty_config, parser=parser)
        args = parser.parse_args("--name Eve".split())

        assert args.name == "Eve"
        assert args.age == 30  # this is the default for --age

    def test_configuration(self, empty_config):
        """Test configuring a default value for an option."""

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(
                help="Your name.", required=True, configurable=True
            )

            def command(self):
                pass

        plugin_name = "greeting"
        configured_name = "Alice"
        config = empty_config
        config.create_section(plugin_name)
        config[plugin_name]["name"] = configured_name

        plugin_instance = Greeting("greeting")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=config, parser=parser)
        args = parser.parse_args([])

        assert args.name == configured_name

    def test_configure_list_like_args(self, empty_config):
        """Test setting configured values for list-like arguments (i.e. with
        `nargs` in argparse).
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            names = plug.cli.option(
                help="one or more names",
                required=True,
                configurable=True,
                argparse_kwargs=dict(nargs="+"),
            )
            numbers = plug.cli.option(
                help="one or more numbers",
                required=True,
                configurable=True,
                converter=int,
                argparse_kwargs=dict(nargs="*"),
            )
            fullnames = plug.cli.option(
                help="one or more full names",
                configurable=True,
                required=True,
                argparse_kwargs=dict(nargs="+"),
            )
            location = plug.cli.option(
                help="your city and country",
                configurable=True,
                required=True,
                argparse_kwargs=dict(nargs=2),
            )

            def command(self):
                pass

        plugin_name = "greeting"
        expected_configured_numbers = (1, 1337, 42, 99)
        expected_configured_names = ("Alice", "Bob", "Eve")
        expected_configured_fullnames = (
            "Alice Alisson",
            "Bob Bobsson",
            "Eve Evesson",
        )
        expected_location = ("Stockholm", "Sweden")
        config = empty_config
        config.create_section(plugin_name)
        section = config[plugin_name]
        section["names"] = " ".join(expected_configured_names)
        section["fullnames"] = " ".join(
            # the full names must be quoted as they contain a space
            f"'{fn}'"
            for fn in expected_configured_fullnames
        )
        section["numbers"] = " ".join(map(str, expected_configured_numbers))
        section["location"] = " ".join(expected_location)

        plugin_instance = Greeting(plugin_name)
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=config, parser=parser)

        args = parser.parse_args([])

        assert args.names == expected_configured_names
        assert args.numbers == expected_configured_numbers
        assert args.fullnames == expected_configured_fullnames
        assert args.location == expected_location

    def test_get_configurable_args_hook_correctly_implemented(self):
        """Only configurable arguments should be returned by the
        get_configurable_args hook.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(
                help="your name", required=True, configurable=True
            )
            age = plug.cli.option(help="your age", configurable=True)
            nationality = plug.cli.option(help="your nationality")

            def command(self):
                pass

        plugin_name = "greeting"
        plugin_instance = Greeting(plugin_name)

        configurable_args = plugin_instance.get_configurable_args()

        assert configurable_args.config_section_name == plugin_name
        assert sorted(configurable_args.argnames) == sorted(["name", "age"])

    def test_get_configurable_args_when_no_args_configurable(self):
        """get_configurable_args should not be implemented if no args are
        configurable.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(help="your name")

            def command(self):
                pass

        plugin_instance = Greeting("greeting")

        assert not hasattr(
            plugin_instance, plug._exthooks.get_configurable_args.__name__
        )

    def test_raises_when_non_configurable_value_is_configured(self):
        """It shouldn't be allowed to have a configuration value for an
        option that is not marked configurable. This is to avoid accidental
        configuration.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(help="Your name.", required=True)

            def command(self):
                pass

        plugin_name = "greeting"
        configured_name = "Alice"
        config = {plugin_name: {"name": configured_name}}
        plugin_instance = Greeting(plugin_name)
        parser = argparse.ArgumentParser()

        with pytest.raises(plug.PlugError) as exc_info:
            plugin_instance.attach_options(config=config, parser=parser)

        assert (
            f"Plugin '{plugin_name}' does not allow 'name' to be configured"
            in str(exc_info.value)
        )

    def test_override_opt_names(self, empty_config):
        """It should be possible to override both the long and short option
        names of an option.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.option(
                short_name="-n",
                long_name="--your-name",
                help="your name",
                required=True,
            )

            def command(self):
                pass

        plugin_instance = Greeting("g")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=empty_config, parser=parser)
        name = "Alice"

        short_opt_args = parser.parse_args(f"-n {name}".split())
        long_opt_args = parser.parse_args(f"--your-name {name}".split())

        assert short_opt_args.name == name
        assert long_opt_args.name == name

    def test_positional_arguments(self, empty_config):
        class Greeting(plug.Plugin, plug.cli.Command):
            name = plug.cli.positional()
            age = plug.cli.positional(converter=int)

            def command(self):
                pass

        plugin_instance = Greeting("g")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=empty_config, parser=parser)

        name = "Alice"
        age = 33
        parsed_args = parser.parse_args(f"{name} {age}".split())

        assert parsed_args.name == name
        assert parsed_args.age == age

    def test_mutex_group_arguments_are_mutually_exclusive(
        self, capsys, empty_config
    ):
        """Test that mutually exclusive arguments can't be provided at the same
        time.
        """

        class Greeting(plug.Plugin, plug.cli.Command):
            age_mutex = plug.cli.mutually_exclusive_group(
                age=plug.cli.option(converter=int),
                old=plug.cli.flag(const=1337),
                __required__=True,
            )

            def command(self):
                pass

        plugin_instance = Greeting("g")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=empty_config, parser=parser)

        with pytest.raises(SystemExit):
            parser.parse_args("--age 12 --old".split())

        assert (
            "error: argument --old: not allowed with argument --age"
            in capsys.readouterr().err
        )

    def test_positionals_not_allowed_in_mutex_group(self):
        """Positional arguments don't make sense in a mutex group."""

        with pytest.raises(ValueError) as exc_info:
            plug.cli.mutually_exclusive_group(
                age=plug.cli.positional(converter=int),
                old=plug.cli.flag(const=1337),
                __required__=True,
            )

        arg_type_str = plug.cli.args._ArgumentType.POSITIONAL.value
        assert f"{arg_type_str} not allowed in mutex" in str(exc_info.value)

    def test_mutex_group_allows_one_argument(self, empty_config):
        """Test that a mutex group allows one argument to be specified."""
        old = 1337

        class Greeting(plug.Plugin, plug.cli.Command):
            age_mutex = plug.cli.mutually_exclusive_group(
                age=plug.cli.option(converter=int),
                old=plug.cli.flag(const=1337),
                __required__=True,
            )

            def command(self):
                pass

        plugin_instance = Greeting("g")
        parser = argparse.ArgumentParser()
        plugin_instance.attach_options(config=empty_config, parser=parser)

        parsed_args = parser.parse_args(["--old"])

        assert parsed_args.old == old

    def test_create_new_category(self):
        """Test that command can be added to a new category."""

        category = plug.cli.category("greetings", action_names=["hello"])

        class Hello(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(action=category.hello)
            name = plug.cli.positional()
            age = plug.cli.positional(converter=int)

            def command(self):
                return plug.Result(
                    name=self.__plugin_name__,
                    msg="Nice!",
                    status=plug.Status.SUCCESS,
                    data={"name": self.name, "age": self.age},
                )

        name = "Bob"
        age = 24
        results_mapping = repobee.run(
            f"greetings hello {name} {age}".split(), plugins=[Hello]
        )
        print(results_mapping)
        _, results = list(results_mapping.items())[0]
        result, *_ = results

        assert result.data["name"] == name
        assert result.data["age"] == age

    def test_add_two_actions_to_new_category(self):
        """Test that it's possible to add multiple actions to a custom
        category.
        """

        category = plug.cli.category(
            name="greetings", action_names=["hello", "bye"]
        )
        hello_instance = None
        bye_instance = None

        class Hello(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(action=category.hello)
            name = plug.cli.positional()

            def command(self):
                nonlocal hello_instance
                hello_instance = self

        class Bye(plug.Plugin, plug.cli.Command):
            __settings__ = plug.cli.command_settings(action=category.bye)
            name = plug.cli.positional()

            def command(self):
                nonlocal bye_instance
                bye_instance = self

        name = "Alice"
        repobee.run(f"greetings hello {name}".split(), plugins=[Hello, Bye])
        repobee.run(f"greetings bye {name}".split(), plugins=[Hello, Bye])

        assert hello_instance.name == name
        assert bye_instance.name == name

    def test_raises_when_both_action_and_category_given(self):
        """It is not allowed to give an Action object to the action argument,
        and at the same time give a Category, as the Action object defines
        both.
        """
        category = plug.cli.category("cat", action_names=["greetings"])

        with pytest.raises(TypeError) as exc_info:

            class Greetings(plug.Plugin, plug.cli.Command):
                __settings__ = plug.cli.command_settings(
                    action=category.greetings, category=category
                )

                def command(self):
                    pass

        assert (
            "argument 'category' not allowed when argument "
            "'action' is an Action object"
        ) in str(exc_info.value)

    def test_parsed_args_are_added_to_self(self):
        """Parsed cli arguments should automatically be added to the plugin
        object instance.
        """
        instance = None

        class Ext(plug.Plugin, plug.cli.Command):
            name = plug.cli.option()
            age = plug.cli.positional(converter=int)
            tolerance = plug.cli.mutually_exclusive_group(
                high=plug.cli.flag(), low=plug.cli.flag(), __required__=True
            )

            def command(self):
                nonlocal instance
                instance = self

        name = "Eve"
        age = 22
        repobee.run(f"ext {age} --name {name} --high".split(), plugins=[Ext])

        assert instance.name == name
        assert instance.age == age
        assert instance.high
        assert not instance.low
        assert isinstance(instance.args, argparse.Namespace)


class TestDeclarativeCommandExtension:
    """Test creating command extensions to existing commands."""

    @pytest.fixture
    def config_file(self, tmpdir):
        config_file = pathlib.Path(str(tmpdir)) / "config.ini"
        config_file.write_text("[repobee]")
        return config_file

    def test_add_required_option_to_config_show(
        self, capsys, tmpdir, config_file
    ):
        """Tests adding a required option to ``config show``."""

        class ConfigShowExt(plug.Plugin, plug.cli.CommandExtension):
            __settings__ = plug.cli.command_extension_settings(
                actions=[plug.cli.CoreCommand.config.show]
            )

            silly_new_option = plug.cli.option(help="your name", required=True)

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

    def test_requires_settings(self):
        """Test that an error is raised if the __settings__ attribute is not
        defined.
        """
        with pytest.raises(plug.PlugError) as exc_info:

            class Ext(plug.Plugin, plug.cli.CommandExtension):
                pass

        assert "CommandExtension must have a '__settings__' attribute" in str(
            exc_info.value
        )

    def test_requires_non_empty_actions_list(self):

        with pytest.raises(ValueError) as exc_info:

            class Ext(plug.Plugin, plug.cli.CommandExtension):
                __settings__ = plug.cli.command_extension_settings(actions=[])

        assert "argument 'actions' must be a non-empty list" in str(
            exc_info.value
        )
