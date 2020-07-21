import sys

from _repobee.main import run
from _repobee.plugin import unregister_all_plugins, try_register_plugin

__all__ = [
    "run",
    "try_register_plugin",
    "unregister_all_plugins",
]


def main():
    import _repobee.main

    _repobee.main.main(sys.argv)


if __name__ == "__main__":
    main()
