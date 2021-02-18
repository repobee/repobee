"""Helpers related to configuration."""
import configparser
import pathlib

__all__ = ["FileBackedConfigParser"]


class FileBackedConfigParser(configparser.ConfigParser):
    """A thin wrapper around :py:class:`configparser.ConfigParser` that
    provides some additional utility functionality for reading from
    and writing to a file.
    """

    def __init__(self, config_path: pathlib.Path):
        super().__init__()
        self.config_path = config_path

    def refresh(self) -> None:
        """Refresh the parser by reading from the config file."""
        self.read(self.config_path)

    def store(self) -> None:
        """Write the current state of the parser to the config file."""
        with open(self.config_path, encoding="utf8", mode="w") as f:
            self.write(f)
