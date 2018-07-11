import sys
import daiquiri
from gits_pet import cli

LOGGER = daiquiri.getLogger(__file__)


def main():
    try:
        parsed_args, api = cli.parse_args(sys.argv[1:])
        cli.handle_parsed_args(parsed_args, api)
    except cli.ParseError as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main()
