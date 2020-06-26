import pytest
from repobee_plug import _pluginmeta
from repobee_plug import _exceptions


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
