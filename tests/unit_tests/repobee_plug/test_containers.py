import argparse
import pytest
from repobee_plug import _containers
from repobee_plug import _exceptions


class TestExtensionCommand:
    def test_raises_if_parser_is_not_a_ExtensionParser(self):
        parser = argparse.ArgumentParser()

        with pytest.raises(_exceptions.ExtensionCommandError) as exc_info:
            _containers.ExtensionCommand(
                parser,
                "test-command",
                "help",
                "description",
                lambda args, api: None,
            )

        assert "parser must be a ExtensionParser" in str(exc_info.value)

    def test_raises_if_callback_is_not_callable(self):
        callback = 2

        with pytest.raises(_exceptions.ExtensionCommandError):
            _containers.ExtensionCommand(
                _containers.ExtensionParser(),
                "test-command",
                "help",
                "description",
                callback,
            )

    def test_requires_api_false_by_default(self):
        exc_command = _containers.ExtensionCommand(
            _containers.ExtensionParser(),
            "test-command",
            "help",
            "description",
            lambda args, api: None,
        )

        assert not exc_command.requires_api

    def test_eq_with_unequal_parsers(self):
        """ExtensionCommands should compare equal if all attributes but the
        parser are the same. The reason for this is that
        argparse.ArgumentParser instances don't compare equal even if they are.
        """
        lhs_parser = _containers.ExtensionParser()
        rhs_parser = _containers.ExtensionParser()
        assert lhs_parser != rhs_parser, "parsers should be unequal"
        command_name = "test-command"
        help = "help"
        description = "description"

        def callback(args, api):
            return None

        lhs = _containers.ExtensionCommand(
            lhs_parser, command_name, help, description, callback
        )
        rhs = _containers.ExtensionCommand(
            lhs_parser, command_name, help, description, callback
        )

        assert lhs == rhs

    def test_requires_api_false_incompatible_with_discovery_parser(self):
        """Test that requires_api=False is incompatible with requesting the
        discovery parser.
        """
        parser = _containers.ExtensionParser()

        def callback(args, api):
            return None

        with pytest.raises(_exceptions.ExtensionCommandError) as exc_info:
            _containers.ExtensionCommand(
                parser=parser,
                name="test",
                description="test",
                help="help",
                callback=callback,
                requires_base_parsers=[_containers.BaseParser.REPO_DISCOVERY],
                requires_api=False,
            )

        assert "REPO_DISCOVERY" in str(exc_info.value)
        assert "requires_api" in str(exc_info.value)


def test_hook_result_deprecation():
    expected = _containers.Result(
        name="test",
        msg="nothing important",
        status=_containers.Status.WARNING,
        data={"hello": "hello"},
    )

    result = _containers.HookResult(
        hook=expected.name,
        msg=expected.msg,
        status=expected.status,
        data=expected.data,
    )

    assert result == expected
    assert result.hook == result.name
