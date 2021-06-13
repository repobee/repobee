"""Helpers related to configuration."""
import configparser
import pathlib
import os

from typing import Any, Optional, List

from typing_extensions import Protocol

from repobee_plug import exceptions

__all__ = ["Config", "ConfigSection"]


class ConfigSection(Protocol):
    """Protocol defining how a section of the config behaves."""

    def __getitem__(self, key: str) -> Any:
        ...

    def __setitem__(self, key: str, value: Any) -> None:
        ...

    def __contains__(self, key: str) -> bool:
        ...


class Config:
    """Object representing RepoBee's config.

    This class defines read-only inheritance. This means that when you read a
    value from the config, for example with :py:meth:`get`, it will do a
    recursive lookup in parent configs.

    Writing to a config object, e.g. ``config[section][option] = value`` does
    *not* respect inheritance, and unconditionally writes to *this* config, and
    not any of its parents. Similarly, writing to disk with :py:meth:`store`
    only writes to the most local config, and not to any of the parent configs.

    .. important::

        Changes to the config are only persisted if the :py:meth:`Config.store`
        method is called.

    .. warning::

        The behavior of this class is currently not stable. Any minor release
        of RepoBee might bring breaking changes.
    """

    CORE_SECTION_NAME = "repobee"
    PARENT_CONFIG_KEY = "parent_config"

    def __init__(self, config_path: pathlib.Path):
        super().__init__()
        self._config_path = config_path
        self._config_parser = configparser.ConfigParser()
        self._parent: Optional[Config] = None
        self.create_section(self.CORE_SECTION_NAME)
        self._check_for_cycle(paths=[])
        self.refresh()

    def refresh(self) -> None:
        """Refresh the parser by reading from the config file. Does nothing if
        the config file does not exist.
        """
        if self._config_path.exists():
            self._config_parser.read(self._config_path)
            raw_parent_path = self.get(
                self.CORE_SECTION_NAME, self.PARENT_CONFIG_KEY
            )
            if raw_parent_path:
                parent_path = self._resolve_absolute_parent_path(
                    raw_parent_path
                )
                self._parent = Config(parent_path)

    def _resolve_absolute_parent_path(
        self, raw_parent_path: str
    ) -> pathlib.Path:
        parent_path = pathlib.Path(raw_parent_path)
        return (
            parent_path
            if parent_path.is_absolute()
            else (self.path.parent / parent_path).resolve(strict=False)
        )

    def store(self) -> None:
        """Write the current state of the config to the config file. If the
        directory does not exist, it is created.
        """
        if not self._config_path.exists():
            os.makedirs(self._config_path.parent, mode=0o700, exist_ok=True)

        with open(self._config_path, encoding="utf8", mode="w") as f:
            self._config_parser.write(f)

    def create_section(self, section_name: str) -> None:
        """Add a section to the config.

        Args:
            section_name: Name of the section.
        """
        return self._config_parser.add_section(section_name)

    def get(
        self, section_name: str, key: str, fallback: Optional[Any] = None
    ) -> Optional[Any]:
        """Get a value from the given section.

        Args:
            section_name: Name of the section.
            key: Key to get the value for.
            fallback: An optional fallback value to use if the section or key
                do not exist.
        Returns:
            The value for the section and key, or the fallback value if neither
            exist.
        """
        return self._config_parser.get(
            section_name,
            key,
            fallback=self.parent.get(section_name, key, fallback)
            if self.parent
            else fallback,
        )

    @property
    def path(self) -> pathlib.Path:
        """Path to the config file."""
        return self._config_path

    @property
    def parent(self) -> Optional["Config"]:
        """Returns the parent config if defined, otherwise None."""
        return self._parent

    @parent.setter
    def parent(self, value: "Config") -> None:
        self._parent = value
        self[self.CORE_SECTION_NAME][self.PARENT_CONFIG_KEY] = str(value.path)
        self._check_for_cycle([])

    def __getitem__(self, section_key: str) -> ConfigSection:
        return _ParentAwareConfigSection(self, section_key)

    def __contains__(self, section_name: str) -> bool:
        return section_name in self._config_parser

    def _check_for_cycle(self, paths: List[pathlib.Path]) -> None:
        """Check if there's a cycle in the inheritance."""
        if self.path in paths:
            cycle = " -> ".join(map(str, paths + [self.path]))
            raise exceptions.PlugError(
                f"Cyclic inheritance detected in config: {cycle}"
            )
        elif self.parent is not None:
            self.parent._check_for_cycle(paths + [self.path])


class _ParentAwareConfigSection:
    """A section of the config that respects sections from parent configs."""

    def __init__(self, config: Config, section_key: str):
        self._config = config
        self._section_key = section_key

    def __getitem__(self, key: str):
        value = self._config.get(self._section_key, key)
        if value is None:
            raise KeyError(key)
        else:
            return value

    def __setitem__(self, key: str, value: Any):
        self._config._config_parser.set(self._section_key, key, value)

    def __contains__(self, key: str) -> bool:
        return self._config.get(self._section_key, key) is not None
