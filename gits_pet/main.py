import sys
import daiquiri

LOGGER = daiquiri.getLogger(__file__)


# if the OAUTH token is not set, OSError is raised
def main():
    try:
        from gits_pet import cli
    except OSError as exc:
        LOGGER.error(str(exc))
        raise SystemExit(
            "Exited because of empty OAUTH token. Set the environment "
            "variable GITS_PET_OAUTH with the value of the token.")

    from gits_pet import exception

    try:
        parsed_args, api = cli.parse_args(sys.argv[1:])
        cli.handle_parsed_args(parsed_args, api)
    except Exception as exc:
        LOGGER.error("{.__class__.__name__}: {}".format(exc, str(exc)))


if __name__ == "__main__":
    main()
