"""ANSI escape codes for prettifying the command line."""

RESET = "\x1b[0m"


class BackgroundColor:
    RED = "\x1b[48;5;1m"
    YELLOW = "\x1b[48;5;3m"
    DARK_GREEN = "\x1b[48;5;22m"
    DARK_GREY = "\x1b[48;5;235m"
    LIGHT_GREY = "\x1b[48;5;239m"


class ForegroundColor:
    WHITE = "\x1b[38;5;15m"
