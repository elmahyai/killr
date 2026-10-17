"""How many ANSI colors the session should use, and whether hyperlinks work."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any

from crayon._options import get_option

truecolor = 256**3

_color_cache: dict[str, int] = {}
_NOT_RSTUDIO = {
    "type": "not_rstudio",
    "dynamic_tty": False,
    "ansi_tty": False,
    "ansi_color": False,
    "num_colors": 1,
}


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
    if text == "" or any(ch in text for ch in ".eE"):
        raise ValueError("cannot coerce this color count to an integer")
    return int(text)


def _is_true(value: object) -> bool:
    return value is True


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


def _os_type() -> str:
    return "windows" if os.name == "nt" else "unix"


def _interactive() -> bool:
    opt = get_option("rlib_interactive")
    if opt is True:
        return True
    if opt is False:
        return False
    if str(get_option("knitr.in.progress", "false")).lower() == "true":
        return False
    if str(get_option("rstudio.notebook.executing", "false")).lower() == "true":
        return False
    if os.environ.get("TESTTHAT") == "true":
        return False
    # R's interactive() is TRUE only in a REPL, not when a terminal is merely attached.
    return bool(sys.flags.interactive)


def _isatty(name: str) -> bool:
    handle = sys.stdout if name == "stdout" else sys.stderr
    try:
        return handle.isatty()
    except Exception:
        return False


def _emacs_version() -> list[float]:
    """The utils.R definition, which is the one left after the package loads."""

    ver = os.environ.get("INSIDE_EMACS", "")
    ver = re.sub(r"[^0-9.]+", "", ver)
    if ver == "":
        return []
    numbers = []
    for part in ver.split("."):
        if part == "":
            continue
        try:
            numbers.append(float(part))
        except ValueError:
            numbers.append(float("nan"))
    return numbers


def _emacs_with_color() -> bool:
    inside = os.environ.get("EMACS", "") != "" or os.environ.get("INSIDE_EMACS", "") != ""
    version = _emacs_version()
    return bool(inside and version and version[0] == version[0] and version[0] >= 23)


_PACKAGE_VERSION = re.compile(r"[0-9]+(?:[.-][0-9]+)+")


def _package_version(text: str, strict: bool = True) -> tuple[int, ...] | None:
    """R's package_version(): digits joined by '.' or '-', at least two parts.

    Strict parsing raises for an invalid string, as R does. Non-strict
    parsing returns None (NA) for it.
    """
    if _PACKAGE_VERSION.fullmatch(text):
        return tuple(int(part) for part in re.split(r"[.-]", text))
    if strict:
        raise ValueError(f"invalid version specification '{text}'")
    return None


def _version_ge(text: str, minimum: str, strict: bool = True) -> bool:
    got = _package_version(text, strict=strict)
    if got is None:
        return False
    # Tuple comparison matches R: a longer version with the same prefix is greater.
    return got >= _package_version(minimum, strict=True)



def _rstudio_type() -> dict[str, Any]:
    if os.environ.get("RSTUDIO", "") != "1":
        return dict(_NOT_RSTUDIO)
    env = {
        "R_BROWSER": os.environ.get("R_BROWSER", ""),
        "R_PDFVIEWER": os.environ.get("R_PDFVIEWER", ""),
        "RSTUDIO": os.environ.get("RSTUDIO", ""),
        "RSTUDIO_TERM": os.environ.get("RSTUDIO_TERM", ""),
        "RSTUDIO_CONSOLE_COLOR": os.environ.get("RSTUDIO_CONSOLE_COLOR", ""),
        "RSTUDIOAPI_IPC_REQUESTS_FILE": os.environ.get("RSTUDIOAPI_IPC_REQUESTS_FILE", ""),
        "XPC_SERVICE_NAME": os.environ.get("XPC_SERVICE_NAME", ""),
        "ASCIICAST": os.environ.get("ASCIICAST", ""),
    }
    args = list(sys.argv)
    tty = False
    try:
        tty = sys.stdin.isatty()
    except Exception:
        tty = False
    gui = str(get_option("R.gui", ""))
    kind = "rstudio_subprocess"
    if env["RSTUDIO"] != "1":
        kind = "not_rstudio"
    elif gui == "RStudio":
        kind = "rstudio_subprocess"
    elif gui == "Rgui":
        kind = "not_rstudio"
    elif tty and env["ASCIICAST"] != "true":
        kind = "rstudio_terminal"
    elif (
        not tty
        and env["RSTUDIO_TERM"] == ""
        and env["R_BROWSER"] == "false"
        and env["R_PDFVIEWER"] == "false"
        and _build_pane(args)
    ):
        kind = "rstudio_build_pane"
    elif env["RSTUDIOAPI_IPC_REQUESTS_FILE"] != "" and "rstudio" in env["XPC_SERVICE_NAME"]:
        kind = "rstudio_job"
    elif env["RSTUDIOAPI_IPC_REQUESTS_FILE"] != "" and any(
        "SourceWithProgress.R" in arg for arg in args
    ):
        kind = "rstudio_job"
    return _caps(kind, env)


def _build_pane(args: list[str]) -> bool:
    if not args:
        return False
    cmd = args[-1].replace('"', "").replace("'", "")
    command = cmd.split("(", 1)[0]
    return command in {"devtools::build", "devtools::test", "devtools::check"}


def _caps(kind: str, env: dict[str, str]) -> dict[str, Any]:
    raw = env.get("RSTUDIO_CONSOLE_COLOR", "")
    try:
        count = _as_integer(raw) if raw != "" else 1
    except ValueError:
        count = 1
    if kind in {"rstudio_console", "rstudio_console_starting", "rstudio_build_pane", "rstudio_job"}:
        return {
            "type": kind,
            "dynamic_tty": kind != "rstudio_job",
            "ansi_tty": False,
            "ansi_color": raw != "",
            "num_colors": count,
        }
    if kind == "rstudio_terminal":
        return {
            "type": kind,
            "dynamic_tty": True,
            "ansi_tty": False,
            "ansi_color": False,
            "num_colors": 1,
        }
    if kind == "not_rstudio":
        return dict(_NOT_RSTUDIO)
    return {
        "type": "rstudio_subprocess",
        "dynamic_tty": False,
        "ansi_tty": False,
        "ansi_color": False,
        "num_colors": 1,
    }


def _guess_tty_colors() -> int:
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return 1
    if re.search(r"^screen|^xterm|^vt100|color|ansi|cygwin|linux", term, re.IGNORECASE):
        return 8
    return 1


def _tput_colors() -> int | None:
    try:
        completed = subprocess.run(
            ["tput", "colors"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    text = completed.stdout.strip().splitlines()
    if not text:
        return None
    try:
        return int(float(text[0]))
    except ValueError:
        return None


def _win10_build() -> int:
    if _os_type() != "windows":
        return 0
    try:
        return int(sys.getwindowsversion().build)
    except Exception:
        return 0


def detect_tty_colors() -> int:
    default = _default_number_of_colors()
    colorterm = os.environ.get("COLORTERM")
    if colorterm is not None:
        if colorterm in {"truecolor", "24bit"}:
            return truecolor
        return 8 if default is None else default
    if _os_type() == "unix" and _emacs_with_color():
        return 8 if default is None else default
    if _os_type() == "windows":
        win10 = _win10_build()
        if win10 >= 10586 and _rstudio_type()["type"] == "rstudio_terminal":
            return 8 if default is None else default
        if win10 >= 14931:
            return truecolor if default is None else default
        if win10 >= 10586:
            return 256 if default is None else default
        if os.environ.get("ConEmuANSI") == "ON" or os.environ.get("CMDER_ROOT", "") != "":
            return 8 if default is None else default
        if os.environ.get("ANSICON", "") != "":
            return 8 if default is None else default
        return 1
    cols = _tput_colors()
    if cols is None:
        return _guess_tty_colors()
    if cols in {-1, 0, 1}:
        return 1
    if cols == 8 and os.environ.get("TERM") == "xterm":
        return 256 if default is None else default
    return cols


def num_ansi_colors(stream: str = "auto") -> int:
    """How many ANSI colors `stream` should use. The stream is resolved the way crayon does."""

    opt = get_option("cli.num_colors")
    if opt is not None:
        return _as_integer(opt)
    env = os.environ.get("R_CLI_NUM_COLORS", "")
    if env != "":
        return _as_integer(env)

    enabled = get_option("crayon.enabled")
    number = get_option("crayon.colors")
    if enabled is not None and not _is_true(enabled):
        return 1
    if _is_true(enabled) and number is not None:
        return _as_integer(number)
    if _is_true(enabled) and number is None:
        default = _default_number_of_colors()
        return 8 if default is None else default

    if "NO_COLOR" in os.environ:
        return 1
    if get_option("knitr.in.progress") is True:
        return 1
    if stream == "auto" and get_option("crayon.sink_output") not in (None, 0):
        return 1
    return _resolved(stream)


def _resolved(stream: str) -> int:
    # get_real_output ignores the requested stream and picks stderr outside a REPL.
    del stream
    name = "stdout" if _interactive() else "stderr"
    if name == "stderr" and get_option("crayon.sink_message") not in (None, 2):
        return 1
    default = _default_number_of_colors()
    if default is not None:
        return int(default)
    gui = str(get_option("R.gui", ""))
    if gui == "AQUA":
        return 1
    rstudio = _rstudio_type()
    if rstudio["type"] in {
        "rstudio_console",
        "rstudio_console_starting",
        "rstudio_build_pane",
        "rstudio_job",
    }:
        return int(rstudio["num_colors"])
    if gui == "Rgui":
        return 1
    if (
        _os_type() == "windows"
        and "--ess" in sys.argv
        and _emacs_with_color()
    ):
        fallback = _default_number_of_colors()
        return 8 if fallback is None else fallback
    if not _isatty(name):
        return 1
    cached = _color_cache.get(name)
    if cached is None:
        cached = detect_tty_colors()
        _color_cache[name] = cached
    return cached


def has_color() -> bool:
    return num_ansi_colors() > 1


def num_colors(forget: bool = False) -> int:
    """num_ansi_colors(), except crayon.colors wins even when crayon.enabled is unset."""

    del forget
    number = get_option("crayon.colors")
    if number is not None:
        return _as_integer(number)
    return num_ansi_colors()


def has_hyperlink() -> bool:
    enabled = get_option("crayon.hyperlink")
    if enabled is not None:
        return enabled is True
    try:
        tty = sys.stdout.isatty()
    except Exception:
        tty = False
    if not tty:
        return False
    if _os_type() == "windows":
        return True
    if os.environ.get("CI", "") != "" or os.environ.get("TEAMCITY_VERSION", "") != "":
        return False
    program = os.environ.get("TERM_PROGRAM", "")
    if program == "iTerm.app":
        if _version_ge(os.environ.get("TERM_PROGRAM_VERSION", ""), "3.1", strict=False):
            return True
    vte = os.environ.get("VTE_VERSION", "")
    if vte != "" and _version_ge(vte, "0.50.1"):
        return True
    return False
