from repobee_plug import config


class TestConfig:
    """Tests for the Config class."""

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
        child = config.Config(child_path, parent=parent)
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
        child = config.Config(child_path, parent=parent)
        fetched_section = child[parent_sec]

        # assert
        assert parent_opt in fetched_section
