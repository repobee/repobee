"""Helpers related to configuration."""
import configparser
import pathlib
import os

from typing import Any, Optional

from typing_extensions import Protocol

__all__ = ["Config"]


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

    .. important::

        Changes to the config are only persisted if the :py:meth:`Config.store`
        method is called.
    """

    def __init__(self, config_path: pathlib.Path):
        super().__init__()
        self._config_path = config_path
        self._config_parser = configparser.ConfigParser()
        self.refresh()

    def refresh(self) -> None:
        """Refresh the parser by reading from the config file. Does nothing if
        the config file does not exist.
        """
        if self._config_path.exists():
            self._config_parser.read(self._config_path)

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
        return self._config_parser.get(section_name, key, fallback=fallback)

    @property
    def path(self) -> pathlib.Path:
        """Path to the config file."""
        return self._config_path

    def __getitem__(self, section_key: str) -> ConfigSection:
        return _ConfigSection(self._config_parser[section_key])

    def __contains__(self, section_name: str) -> bool:
        return section_name in self._config_parser


class _ConfigSection:
    """A section of the config."""

    def __init__(self, section: ConfigSection):
        self._section = section

    def __getitem__(self, key: str):
        return self._section[key]

    def __setitem__(self, key: str, value: Any):
        self._section[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._section
