import sys
import daiquiri
from gits_pet import cli
from gits_pet import exception

LOGGER = daiquiri.getLogger(__file__)


def main():
    try:
        parsed_args, api = cli.parse_args(sys.argv[1:])
        cli.handle_parsed_args(parsed_args, api)
    except Exception as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main()
