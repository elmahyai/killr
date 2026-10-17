"""Terminal capability checks used by the cursor helpers.

A non-terminal stream does nothing, which is what Rscript does here.
"""

from __future__ import annotations

import os
import sys

from cli._options import get_option


def _isatty(stream: str) -> bool:
    handle = sys.stdout if stream == "stdout" else sys.stderr
    try:
        return bool(handle.isatty())
    except Exception:
        return False


def _resolve(stream: str) -> str:
    if stream in ("stderr", "message"):
        return "stderr"
    if stream == "stdout":
        return "stdout"
    return "stdout" if sys.stdin.isatty() and _isatty("stdout") else "stderr"


def is_ansi_tty(stream="auto") -> bool:
    """Whether this stream should receive ANSI cursor and style sequences."""

    option = get_option("cli.ansi")
    if option is True:
        return True
    if option is False:
        return False
    name = _resolve(stream)
    if os.environ.get("RSTUDIO") == "1":
        return False
    return (
        _isatty(name)
        and os.name == "posix"
        and os.environ.get("R_GUI_APP_VERSION", "") == ""
        and os.environ.get("EMACS", "") == ""
        and os.environ.get("INSIDE_EMACS", "") == ""
        and os.environ.get("TERM", "") != "dumb"
    )


def is_dynamic_tty(stream="auto") -> bool:
    """Whether a carriage return can redraw the current line."""

    option = get_option("cli.dynamic")
    if option is not None:
        return option is True
    env = os.environ.get("R_CLI_DYNAMIC", "")
    if env != "":
        return env.strip().lower() in ("true", "1", "yes")
    return _isatty(_resolve(stream))


def ansi_hide_cursor(stream="auto") -> None:
    """Hide the cursor when the stream is an ANSI terminal."""

    if os.environ.get("R_CLI_HIDE_CURSOR") == "false":
        return
    if is_ansi_tty(stream):
        sys.stdout.write("\x1b[?25l")


def ansi_show_cursor(stream="auto") -> None:
    """Show the cursor when the stream is an ANSI terminal."""

    if os.environ.get("R_CLI_HIDE_CURSOR") == "false":
        return
    if is_ansi_tty(stream):
        sys.stdout.write("\x1b[?25h")


def ansi_with_hidden_cursor(expr, stream="auto"):
    """Hide the cursor while expr runs. expr is called when it is a function."""

    ansi_hide_cursor(stream)
    try:
        return expr() if callable(expr) else expr
    finally:
        ansi_show_cursor()
