import pytest
from repobee_plug import config
from repobee_plug import exceptions


class TestConfig:
    """Tests for the Config class."""

    def test_detects_cyclic_inheritance(self, tmp_path):
        # arrange

        grandparent_path = tmp_path / "otherdir" / "grandparent.ini"
        parent_path = tmp_path / "dir" / "parent.ini"
        child_path = tmp_path / "repobee.ini"

        grandparent = config.Config(grandparent_path)

        parent = config.Config(parent_path)
        parent.parent = grandparent

        child = config.Config(child_path)
        child.parent = parent

        # act/assert
        with pytest.raises(exceptions.PlugError) as exc_info:
            grandparent.parent = child

        cycle = " -> ".join(
            map(
                str,
                [grandparent_path, child_path, parent_path, grandparent_path],
            )
        )
        assert f"Cyclic inheritance detected in config: {cycle}" in str(
            exc_info.value
        )

    def test_get_option_from_parent(self, tmp_path):
        # arrange

        parent_path = tmp_path / "dir" / "parent.ini"
        child_path = tmp_path / "repobee.ini"

        parent = config.Config(parent_path)
        parent_sec = "some-section"
        parent_opt = "some-option"
        parent_val = "some-value"
        parent.create_section(parent_sec)
        parent[parent_sec][parent_opt] = parent_val

        # act
        child = config.Config(child_path)
        child.parent = parent
        fetched_val = child.get(parent_sec, parent_opt)

        # assert
        assert fetched_val == parent_val

    def test_resolves_section_from_parent(self, tmp_path):
        # arrange

        parent_path = tmp_path / "dir" / "parent.ini"
        child_path = tmp_path / "repobee.ini"

        parent = config.Config(parent_path)
        parent_sec = "some-section"
        parent_opt = "some-option"
        parent_val = "some-value"
        parent.create_section(parent_sec)
        parent[parent_sec][parent_opt] = parent_val

        # act
        child = config.Config(child_path)
        child.parent = parent
        fetched_section = child[parent_sec]

        # assert
        assert parent_opt in fetched_section
        assert fetched_section[parent_opt] == parent_val

    def test_section_contains_values_from_parent_and_child(self, tmp_path):
        # arrange
        parent_path = tmp_path / "dir" / "parent.ini"
        child_path = tmp_path / "repobee.ini"

        parent = config.Config(parent_path)
        parent_sec = "some-section"
        parent_opt = "some-option"
        parent_val = "some-value"
        parent.create_section(parent_sec)
        parent[parent_sec][parent_opt] = parent_val

        child_opt = "other-option"
        child_val = "other-value"
        child = config.Config(child_path)
        child.parent = parent
        child.create_section("some-section")
        child[parent_sec][child_opt] = child_val

        # act
        section = child[parent_sec]
        fetched_parent_value = section[parent_opt]
        fetched_child_value = section[child_opt]

        # assert
        assert fetched_parent_value == parent_val
        assert fetched_child_value == child_val

    def test_key_error_on_getitem_for_non_existent_key(self, tmp_path):
        # arrange
        parent_path = tmp_path / "dir" / "parent.ini"
        child_path = tmp_path / "repobee.ini"

        parent = config.Config(parent_path)
        parent_sec = "some-section"
        parent_opt = "some-option"
        parent_val = "some-value"
        parent.create_section(parent_sec)
        parent[parent_sec][parent_opt] = parent_val

        child = config.Config(child_path)
        child.parent = parent

        # act/assert
        non_existing_key = "thiskeydoesntexist"
        with pytest.raises(KeyError) as exc_info:
            child[parent_sec][non_existing_key]

        assert non_existing_key in str(exc_info.value)
