"""How many ANSI colors the session should use."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

from cli._options import get_option

truecolor = 256**3

_color_cache: dict[str, int] = {}


def _as_integer(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("cannot coerce this color count to an integer")
        return int(value)
    text = str(value).strip()
    if text == "":
        raise ValueError("cannot coerce an empty color count")
    return int(float(text)) if "." in text else int(text)


def _is_count(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and value != int(value):
        return False
    return int(value) >= 0


def _default_number_of_colors() -> int | None:
    default = get_option("cli.default_num_colors")
    if default is None:
        return None
    if not _is_count(default):
        return None
    return int(default)


def _interactive() -> bool:
    return bool(getattr(sys, "ps1", None)) and sys.stdin.isatty()


def _stream_name(stream: str) -> str:
    if stream == "auto":
        return "stdout" if _interactive() else "stderr"
    if stream in ("message", "stderr"):
        return "stderr"
    if stream == "stdout":
        return "stdout"
    raise ValueError("stream must be auto, message, stdout, or stderr")


def _isatty(name: str) -> bool:
    handle = sys.stdout if name == "stdout" else sys.stderr
    try:
        return handle.isatty()
    except Exception:
        return False


def _emacs_version() -> list[float]:
    ver = os.environ.get("INSIDE_EMACS", "")
    if ver == "":
        return []
    ver = ver.replace("'", "")
    parts = ver.split(",")[0].split(".")
    numbers = []
    for part in parts:
        try:
            numbers.append(float(part))
        except ValueError:
            numbers.append(float("nan"))
    return numbers


def _emacs_with_color() -> bool:
    if os.environ.get("EMACS", "") == "" and os.environ.get("INSIDE_EMACS", "") == "":
        return False
    version = _emacs_version()
    return bool(version) and version[0] == version[0] and version[0] >= 23


def _guess_tty_colors() -> int:
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return 1
    if re.search(r"^screen|^xterm|^vt100|color|ansi|cygwin|linux", term, re.IGNORECASE):
        return 8
    return 1


def _tput_colors() -> int | None:
    if shutil.which("tput") is None:
        return None
    try:
        completed = subprocess.run(
            ["tput", "colors"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    text = (completed.stdout or "").strip().split()
    if not text:
        return None
    try:
        return int(float(text[0]))
    except ValueError:
        return None


def detect_tty_colors() -> int:
    """Terminal color detection used when no cli option overrides it."""

    default = _default_number_of_colors()
    colorterm = os.environ.get("COLORTERM")
    if colorterm is not None:
        if colorterm in ("truecolor", "24bit"):
            return truecolor
        return 8 if default is None else default

    if os.name != "nt" and _emacs_with_color():
        return 8 if default is None else default

    if os.name == "nt":
        if os.environ.get("ConEmuANSI") == "ON" or os.environ.get("CMDER_ROOT", "") != "":
            return 8 if default is None else default
        if os.environ.get("ANSICON", "") != "":
            return 8 if default is None else default
        return 1

    cols = _tput_colors()
    if cols is None:
        return _guess_tty_colors()
    if cols in (-1, 0, 1):
        return 1
    if cols == 8 and os.environ.get("TERM") == "xterm":
        return 256 if default is None else default
    return cols


def num_ansi_colors(stream: str = "auto") -> int:
    """Number of ANSI colors to use for ``stream``.

    ``cli.num_colors`` wins, then ``R_CLI_NUM_COLORS``, then the crayon
    compatibility options, then ``NO_COLOR``. A non-terminal stream is 1.
    """

    opt = get_option("cli.num_colors", None)
    if opt is not None:
        return _as_integer(opt)

    env = os.environ.get("R_CLI_NUM_COLORS", "")
    if env != "":
        return _as_integer(env)

    crayon_enabled = get_option("crayon.enabled", None)
    crayon_colors = get_option("crayon.colors", None)
    if crayon_enabled is not None and crayon_enabled is not True:
        return 1
    if crayon_enabled is True and crayon_colors is not None:
        return _as_integer(crayon_colors)
    if crayon_enabled is True and crayon_colors is None:
        default = _default_number_of_colors()
        return 8 if default is None else default

    if "NO_COLOR" in os.environ:
        return 1
    if get_option("knitr.in.progress") is True:
        return 1

    name = _stream_name(stream)
    if not _isatty(name):
        return 1

    if os.environ.get("RSTUDIO") == "1":
        # RStudio color counts need the rstudioapi session. Outside that
        # session the installed function does not take this branch.
        pass

    default = _default_number_of_colors()
    if default is not None:
        return default

    cached = _color_cache.get(name)
    if cached is None:
        cached = detect_tty_colors()
        _color_cache[name] = cached
    return cached
