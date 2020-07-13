import sys

from _repobee.main import main
from _repobee.plugin import unregister_all_plugins, try_register_plugin

__all__ = [
    main.__name__,
    try_register_plugin.__name__,
    unregister_all_plugins.__name__,
]

if __name__ == "__main__":
    main(sys.argv)
