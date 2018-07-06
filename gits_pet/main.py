import sys
from gits_pet import cli


def main():
    parsed_args, api = cli.parse_args(sys.argv[1:])
    cli.handle_parsed_args(parsed_args, api)


if __name__ == "__main__":
    main()
