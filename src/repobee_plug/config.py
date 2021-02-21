"""Helpers related to configuration."""
import configparser
import pathlib
import os

from typing import Any

from typing_extensions import Protocol

__all__ = ["Config"]


class _SectionProxyIsh(Protocol):
    def __getitem__(self, key: str) -> Any:
        ...

    def __setitem__(self, key: str, value: Any) -> None:
        ...


class _ConfigSection:
    """A section of the config."""

    def __init__(self, section: _SectionProxyIsh):
        self._section = section

    def __getitem__(self, key: str):
        return self._section[key]

    def __setitem__(self, key: str, value: Any):
        self._section[key] = value


class Config:
    """Object representing RepoBee's config."""

    def __init__(self, config_path: pathlib.Path):
        super().__init__()
        self._config_path = config_path
        self._config_parser = configparser.ConfigParser()
        self.refresh()

    def refresh(self) -> None:
        """Refresh the parser by reading from the config file."""
        self._config_parser.read(self._config_path)

    def store(self) -> None:
        """Write the current state of the parser to the config file. If the
        directory does not exist, it is created.
        """
        if not self._config_path.exists():
            os.makedirs(self._config_path.parent, exist_ok=True)

        with open(self._config_path, encoding="utf8", mode="w") as f:
            self._config_parser.write(f)

    def __getitem__(self, section_key: str) -> _ConfigSection:
        return _ConfigSection(self._config_parser[section_key])
