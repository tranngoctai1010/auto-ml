# @author: Tran Ngoc Tai <taitngch240051@gmail.com>

from __future__ import annotations

import logging
import os
import platform
import re
import sys
import warnings
from pathlib import Path

import colorama

LOGGING_NAME = "automl"
SUCCESS = 25
WINDOWS = platform.system() == "Windows"

# -----------------------------------------------------------------------------
# Logging configuration parameters (read from environment variables)
# These control the behavior of PrettyFormatter instance.
# -----------------------------------------------------------------------------
VERBOSE: bool = (
    os.getenv("AUTOML_VERBOSE", "true").lower() == "true"
)  # Enable verbose logging.
NO_COLOR = bool(os.getenv("NO_COLOR"))  # Disable ANSI colors.
NO_EMOJI = bool(os.getenv("NO_EMOJI"))  # Disable emojis in logs.
NO_TIME = bool(os.getenv("NO_TIME"))  # Disable timestamps.
LOG_FILE = os.getenv("LOG_FILE")  # Path to log file (Optional).

# Stronger ANSI escape sequence regex (CSI)
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def colorstr(*input: str | Path) -> str:
    r"""
    Color a string based on the provided color and style arguments using ANSI escape codes.

    This function can be called in two ways:
        - colorstr('color', 'style', 'your string')
        - colorstr('your string')

    In the second form, 'blue' and 'bold' will be applied by default.

    Args:
        *input (str | Path): A sequence of strings where the first n-1 strings are color and style arguments,
                      and the last string is the one to be colored.

    Returns:
        (str): The input string wrapped with ANSI escape codes for the specified color and style.

    Notes:
        Supported Colors and Styles:
        - Basic Colors: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        - Bright Colors: 'bright_black', 'bright_red', 'bright_green', 'bright_yellow',
                       'bright_blue', 'bright_magenta', 'bright_cyan', 'bright_white'
        - Misc: 'end', 'bold', 'underline'

    Examples:
        >>> colorstr("blue", "bold", "hello world")
        >>> "\033[34m\033[1mhello world\033[0m"

    References:
        https://en.wikipedia.org/wiki/ANSI_escape_code
    """
    *args, string = input if len(input) > 1 else ("blue", "bold", input[0])
    colors = {
        "black": "\033[30m",  # basic colors
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bright_black": "\033[90m",  # bright colors
        "bright_red": "\033[91m",
        "bright_green": "\033[92m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
        "bright_magenta": "\033[95m",
        "bright_cyan": "\033[96m",
        "bright_white": "\033[97m",
        "end": "\033[0m",  # misc
        "bold": "\033[1m",
        "underline": "\033[4m",
    }
    return "".join(colors[str(x)] for x in args) + str(string) + colors["end"]


def remove_colorstr(input_string: str):
    """
    Remove ANSI escape codes from a string, effectively removing text colors and styles.

    This function strips ANSI escape sequences (used for terminal text formatting such as
    colors, bold, and underline) from the given string, returning a plain-text version.
    It is especially useful for cleaning log outputs or text files where colored text
    may not be supported or desired.

    Args:
        input_string (str): The input string that may contain ANSI color or style codes.

    Returns:
        (str): A new string with all ANSI escape sequences removed, leaving plain text only.

    Notes:
        - ANSI escape codes typically start with the ESC character (`\x1b`) followed by `[`.
        - This function removes sequences that match the pattern `\x1b[[0-9;]*[A-Za-z]`.

    Examples:
        >>> remove_colorstr(colorstr("blue", "bold", "hello world"))
        'hello world'
        >>> remove_colorstr("\\x1b[31mError: Something failed\\x1b[0m")
        'Error: Something failed'

    References:
        https://en.wikipedia.org/wiki/ANSI_escape_code
    """
    ansi_escape = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
    return ansi_escape.sub("", input_string)


def remove_emoji(input_string: str) -> str:
    """
    Remove all emoji characters from a string.

    This function strips most common Unicode emoji characters from the input string,
    including pictographs, symbols, and flag emojis. It is useful for cleaning log
    outputs or text data where emoji rendering is unnecessary or undesired.

    Args:
        input_string (str): The input string potentially containing emoji characters.

    Returns:
        (str): A new string with all emoji characters removed.

    Notes:
        The Unicode ranges covered include:
        - Miscellaneous Symbols and Pictographs (U+1F300–U+1FAFF)
        - Miscellaneous Symbols (U+2600–U+27BF)
        - Regional Indicator Symbols (flags, U+1F1E6–U+1F1FF)

    Examples:
        >>> remove_emoji("Hello 🎉🐍🚀")
        'Hello '
        >>> remove_emoji("Success ✅ and Warning ⚠️")
        'Success  and Warning '

    References:
        https://en.wikipedia.org/wiki/Unicode_block#Emoticons
        https://unicode.org/emoji/charts/full-emoji-list.html
    """
    emoji_pattern = re.compile(
        r"[\U0001F300-\U0001FAFF"  # Misc Symbols & Pictographs + Supplemental Symbols & Pictographs
        r"\U00002600-\U000027BF"  # Misc symbols
        r"\U0001F1E6-\U0001F1FF]+",  # Flags
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", input_string)


def _emojis(s: str) -> str:
    """
    Replace emojis when the terminal encoding cannot render them.
    Mappings:
      🐛 -> DEBUG, 📘 -> INFO, 🎉 -> SUCCESS, 🚧 -> WARNING, 🐞 -> ERROR, 💀 -> CRITICAL
    """
    try:
        s.encode(sys.stdout.encoding or "utf-8", errors="strict")
        return s
    except Exception:
        # Remove common emojis in the example.
        return (
            s.replace("🐛", "DEBUG")
            .replace("📘", "INFO")
            .replace("🎉", "SUCCESS")
            .replace("🚧", "WARNING")
            .replace("🐞", "ERROR")
            .replace("💀", "CRITICAL")
        )


class PrettyFormatter(logging.Formatter):
    """
    A custom logging formatter that enhances log records with colors, emojis, and timestamps.

    This formatter provides visually enriched log output for console and file logging.
    It supports optional ANSI colors, emoji icons, and timestamps for different log levels.
    Color and emoji display can be toggled independently via the `use_color` and `use_emoji`
    flags. The `show_time` flag controls whether timestamps are included in the formatted output.

    Supported log levels:
        - DEBUG 🐛
        - INFO 📘
        - SUCCESS 🎉
        - WARNING 🚧
        - ERROR 🐞
        - CRITICAL 💀

    Args:
        use_color (bool, optional): Whether to include ANSI color codes in the log output.
            Defaults to True.
        use_emoji (bool, optional): Whether to include emojis for each log level.
            Defaults to True.
        show_time (bool, optional): Whether to display a timestamp at the beginning of each log line.
            Defaults to True.
        **kwargs: Additional keyword arguments (ignored but accepted for compatibility).

    Attributes:
        LEVEL_STYLE (dict[int, tuple[str, str, str]]): Mapping of log levels to their label,
            color, and emoji representations. For example:
            ```python
            {
                logging.INFO: ("INFO", "blue", "📘"),
                logging.ERROR: ("ERROR", "red", "🐞"),
            }
            ```

    Returns:
        (str): A formatted log string containing level, timestamp, message, and optionally colors/emojis.

    Examples:
        >>> import logging
        >>> logger = logging.getLogger("demo")
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(PrettyFormatter(use_color=True, use_emoji=True, show_time=True))
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.DEBUG)
        >>> logger.info("Application started")
        2025-10-06 14:32:15 INFO 📘 Application started

    Notes:
        - When `use_color=False`, all ANSI escape codes are stripped via `remove_colorstr()`.
        - When `use_emoji=False`, emojis are removed via `remove_emoji()`.
        - The `_emojis()` helper ensures compatibility with terminals that cannot render emojis.
        - File handlers should typically set both `use_color=False` and `use_emoji=False`
          to keep log files plain-text friendly.

    References:
        https://docs.python.org/3/library/logging.html#logging.Formatter
        https://en.wikipedia.org/wiki/ANSI_escape_code
    """

    LEVEL_STYLE = {
        logging.DEBUG: ("DEBUG", "cyan", "🐛"),
        logging.INFO: ("INFO", "blue", "📘"),
        SUCCESS: ("SUCCESS", "green", "🎉"),
        logging.WARNING: ("WARNING", "yellow", "🚧"),
        logging.ERROR: ("ERROR", "red", "🐞"),
        logging.CRITICAL: ("CRITICAL", "magenta", "💀"),
    }

    def __init__(
        self,
        *,
        use_color: bool = True,
        use_emoji: bool = True,
        show_time: bool = True,
        **kwargs,
    ):
        # don't use fmt with asctime to control its position ourselves
        super().__init__("%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        self.use_color = use_color
        self.use_emoji = use_emoji
        self.show_time = show_time

        if kwargs:
            warnings.warn(
                f"Ignored unknown kwarg(s): {list(kwargs)}", UserWarning, stacklevel=2
            )

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # show exception text if present
        if record.exc_info:
            try:
                msg = f"{msg}\n{self.formatException(record.exc_info)}"
            except Exception:
                pass

        label, color, emoji = self.LEVEL_STYLE.get(
            record.levelno, (record.levelname, None, "")
        )

        level_tag = label
        if self.use_color and color:
            level_tag = colorstr("bold", color, label)
        if self.use_emoji and emoji:
            level_tag = f"{level_tag} {emoji}"

        parts = []
        if self.show_time:
            ts_txt = self.formatTime(record, self.datefmt)
            parts.append(
                colorstr(color, "bold", ts_txt)
                if (self.use_color and color)
                else ts_txt
            )
        parts.append(level_tag)
        parts.append(msg)

        out = " ".join(p for p in parts if p)

        if not self.use_color:
            out = remove_colorstr(out)  # Delete ANSI color

        # Remove all emoji characters (covering most common Unicode emoji ranges)
        if not self.use_emoji:
            out = remove_emoji(out)
        return _emojis(out)


def _register_success_level() -> None:
    """Register the SUCCESS logging level and Logger.success()."""
    logging.addLevelName(SUCCESS, "SUCCESS")

    def success(self, message, *args, **kwargs):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, **kwargs)

    logging.Logger.success = success  # type: ignore[attr-defined]


def set_logging(
    name: str = "logger",
    verbose: bool = True,
    log_file: str | None = None,
) -> logging.Logger:
    """
    Create and configure a logger with optional colorized console and file output.

    This function sets up a Python logger that can output log messages to both the console
    and an optional log file. It uses the `PrettyFormatter` class to format log records
    with colors, emojis, and timestamps. The console output supports colored and emoji-rich
    logs, while file output is plain-text (UTF-8) without colors or emojis.

    The function also registers a custom `SUCCESS` log level (value 25) so that loggers
    can use `logger.success("message")` in addition to the standard logging levels.

    Args:
        name (str, optional): The name of the logger instance. Defaults to `"logger"`.
        verbose (bool, optional): If True, sets the logger level to `DEBUG`.
            If False, sets the logger level to `INFO`. Defaults to True.
        log_file (str | None, optional): Path to a log file for saving logs.
            If provided, a file handler is added with UTF-8 encoding and no color/emoji formatting.

    Returns:
        (logging.Logger): A configured `Logger` instance ready for use.

    Notes:
        - The custom `SUCCESS` level (25) is added via `_register_success_level()`.
        - On Windows systems, `colorama.just_fix_windows_console()` is called to enable
          proper color rendering in terminals.
        - If the same logger name is reused, this function updates existing handlers
          rather than adding duplicates.
        - The file handler (if created) always writes logs in UTF-8 and excludes ANSI codes
          or emojis for clean text files.
        - Console formatting behavior respects the environment variables:
            - `NO_COLOR`: disables colors.
            - `NO_EMOJI`: disables emojis.
            - `NO_TIME`: hides timestamps.

    Examples:
        >>> logger = set_logging("myapp", verbose=True, log_file="app.log")
        >>> logger.debug("Debug message 🐛")
        >>> logger.info("Application started 📘")
        >>> logger.success("Process completed 🎉")
        >>> logger.warning("Low memory 🚧")
        >>> logger.error("Unexpected error 🐞")
        >>> logger.critical("System crash 💀")

        # Console output: colored + emojis + timestamps
        # app.log content: plain UTF-8 text (no color, no emoji)

    References:
        https://docs.python.org/3/library/logging.html
        https://pypi.org/project/colorama/
    """
    level = logging.DEBUG if verbose else logging.INFO
    _register_success_level()

    # Better Windows console handling (colors/emoji)
    try:
        if WINDOWS:
            colorama.just_fix_windows_console()
    except Exception:
        pass

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # ---- Console handler ----
    console_fmt = PrettyFormatter(
        use_color=not NO_COLOR,
        use_emoji=not NO_EMOJI,
        show_time=not NO_TIME,
    )

    if not any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in logger.handlers
    ):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(console_fmt)
        logger.addHandler(ch)
    else:
        for h in logger.handlers:
            if (
                isinstance(h, logging.StreamHandler)
                and getattr(h, "stream", None) is sys.stdout
            ):
                h.setLevel(level)
                h.setFormatter(console_fmt)

    # ---- File handler (always no color/emoji) ----
    if log_file and not any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == os.path.abspath(log_file)
        for h in logger.handlers
    ):
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(
            PrettyFormatter(
                use_color=False,
                use_emoji=False,
                show_time=not NO_TIME,
            )
        )
        logger.addHandler(fh)

    return logger


# Set logger (used in train.py, val.py, predict.py, etc.)
LOGGER = set_logging(LOGGING_NAME, verbose=VERBOSE, log_file=LOG_FILE)

# Silence noisy third-party loggers
for _name in ("sentry_sdk", "urllib3.connectionpool"):
    logging.getLogger(_name).setLevel(logging.CRITICAL + 1)
