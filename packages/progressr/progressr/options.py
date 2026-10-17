"""progressr options, assertions, and small R helpers."""

from __future__ import annotations

import ast
import inspect
import math
import os
import sys


class ProgressrError(Exception):
    """An error progressr reports, with the R message."""


_OPTIONS: dict = {}

_LEFT = "\u2018"
_RIGHT = "\u2019"


def squote(text) -> str:
    """R 4.5 sQuote: Unicode quotes U+2018 and U+2019."""
    return f"{_LEFT}{text}{_RIGHT}"


def dquote(text) -> str:
    return f"\u201c{text}\u201d"


def stdin_is_tty() -> bool:
    """R interactive() is false when Rscript's stdin is not a terminal."""
    try:
        return bool(sys.stdin.isatty())
    except Exception:
        return False


def _as_logical_scalar(value):
    """R as.logical for one value. None means NA."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "t"}:
            return True
        if token in {"false", "f"}:
            return False
        return None
    return None


def get_option(name, default=None):
    if name in _OPTIONS:
        return _OPTIONS[name]
    return default


def set_option(name, value):
    """R options(name = NULL) removes the option."""
    if value is None:
        _OPTIONS.pop(name, None)
    else:
        _OPTIONS[name] = value
    return value


_MISSING = object()


def options_set(pairs: dict):
    """Set several options and return the previous values."""
    previous = {}
    for name, value in pairs.items():
        previous[name] = _OPTIONS[name] if name in _OPTIONS else _MISSING
        set_option(name, value)
    return previous


def options_restore(previous: dict) -> None:
    for name, value in previous.items():
        if value is _MISSING:
            _OPTIONS.pop(name, None)
        else:
            _OPTIONS[name] = value


def _env_value(suffix: str):
    return os.environ.get(f"R_PROGRESSR_{suffix}", "")


def _init_options() -> None:
    interactive = stdin_is_tty()
    enable_env = _env_value("ENABLE")
    if enable_env == "interactive":
        set_option("progressr.enable", interactive)
    elif enable_env.strip():
        coerced = _as_logical_scalar(enable_env.strip())
        set_option("progressr.enable", interactive if coerced is None else coerced)
    else:
        set_option("progressr.enable", interactive)

    defaults = {
        "clear": (True, "CLEAR"),
        "enable_after": (0.0, "ENABLE_AFTER"),
        "interval": (0.0, "INTERVAL"),
        "times": (math.inf, "TIMES"),
        "interrupts": (True, "INTERRUPTS"),
        "debug": (False, "DEBUG"),
    }
    for name, (default, env_name) in defaults.items():
        raw = _env_value(env_name)
        key = f"progressr.{name}"
        if not raw.strip():
            set_option(key, default)
            continue
        if isinstance(default, bool):
            coerced = _as_logical_scalar(raw.strip())
            set_option(key, default if coerced is None else coerced)
        else:
            try:
                number = float(raw.strip())
            except ValueError:
                number = default
            if name == "times" and raw.strip().lower() in {"inf", "+inf", "infinity"}:
                number = math.inf
            set_option(key, number)


_init_options()


def match_arg(arg, choices):
    """R match.arg. A vector equal to the choices selects the first. A unique prefix matches."""
    choices = tuple(choices)
    if isinstance(arg, (list, tuple)):
        if list(arg) == list(choices):
            return choices[0]
        if len(arg) != 1:
            raise ProgressrError(f"{squote('arg')} must be of length 1")
        arg = arg[0]
    if not isinstance(arg, str):
        raise ProgressrError(f"{squote('arg')} must be of length 1")
    if arg in choices:
        return arg
    matches = [choice for choice in choices if choice.startswith(arg)]
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(squote(choice) for choice in choices)
    if not matches:
        raise ProgressrError(f"'arg' should be one of {listed}")
    raise ProgressrError(f"'arg' matches multiple choices: {', '.join(matches)}")


def _is_r_true(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict, str)):
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _call_arg_sources(frame) -> list[str]:
    try:
        info = inspect.getframeinfo(frame)
        filename = info.filename
        if not filename or filename.startswith("<"):
            return []
        with open(filename, encoding="utf-8") as handle:
            lines = handle.readlines()
        text = ""
        depth = 0
        started = False
        for line in lines[info.lineno - 1 :]:
            text += line
            for char in line:
                if char == "(":
                    depth += 1
                    started = True
                elif char == ")":
                    depth -= 1
            if started and depth <= 0:
                break
        source = text.strip()
        tree = ast.parse(source)
        call = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "stop_if_not":
                call = node
                break
        if call is None:
            return []
        return [ast.get_source_segment(source, arg) or "" for arg in call.args]
    except Exception:
        return []


def stop_if_not(*values) -> None:
    """Raise when a condition is not a length-one TRUE. Quotes match R 4.5 sQuote."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    texts = _call_arg_sources(caller) if caller is not None else []
    for index, value in enumerate(values):
        if _is_r_true(value):
            continue
        text = texts[index] if index < len(texts) and texts[index] else "FALSE"
        raise ProgressrError(f"{squote(text)} is not TRUE")


def hpaste(values, sep="", collapse=", ", last_collapse=None, max_head=None, max_tail=None) -> str:
    """Abbreviated paste used by the print methods."""
    if values is None:
        return ""
    if isinstance(values, str):
        parts = [values]
    else:
        parts = ["" if item is None else str(item) for item in values]
    if not parts:
        return ""
    if collapse is None:
        return sep.join(parts) if False else parts[0]
    if last_collapse is None:
        last_collapse = collapse
    if max_head is None:
        max_head = 3 if last_collapse == collapse else math.inf
    if max_tail is None:
        max_tail = 1 if math.isfinite(max_head) else math.inf
    if len(parts) > max_head + max_tail + 1:
        head = parts[: int(max_head)]
        tail = parts[-int(max_tail) :] if max_tail else []
        parts = head + ["..."] + tail
    if len(parts) == 1:
        return parts[0]
    if last_collapse == collapse:
        return collapse.join(parts)
    return collapse.join(parts[:-1]) + last_collapse + parts[-1]


_MAIN_PID = None


def is_fork_child() -> bool:
    """True after a fork changes the process id recorded at import."""
    global _MAIN_PID
    pid = os.getpid()
    if _MAIN_PID is None:
        _MAIN_PID = pid
    return pid != _MAIN_PID


is_fork_child()


def file_test_f(path) -> bool:
    """R file_test('-f', path). Existence of a regular file."""
    return os.path.isfile(os.path.expanduser(str(path)))
