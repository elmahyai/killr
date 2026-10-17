"""stopifnot, warning and message suppression, capture, and get0."""

from __future__ import annotations

import io
import sys
from contextvars import ContextVar

from backports._values import NA, BackportError, is_na, match_arg
from backports.simple import Condition

__all__ = [
    "capture_output",
    "get0",
    "message",
    "stopifnot",
    "suppressMessages",
    "suppressWarnings",
]

_message_sink: ContextVar = ContextVar("backports_message_sink", default=None)


def stopifnot(**checks):
    for name, value in checks.items():
        if _all_true(value):
            continue
        if name:
            raise BackportError(name)
        raise BackportError("is not TRUE")
    return None


def _all_true(value) -> bool:
    items = list(value) if isinstance(value, (list, tuple)) else [value]
    if not items:
        return False
    for item in items:
        if not isinstance(item, bool) or is_na(item) or item is not True:
            return False
    return True


def suppressWarnings(expr, classes="warning"):
    return _suppress(expr, classes)


def suppressMessages(expr, classes="message"):
    return _suppress(expr, classes)


def _suppress(expr, classes):
    try:
        return expr() if callable(expr) else expr
    except Condition as caught:
        if caught.inherits(classes):
            return None
        raise


def message(text):
    line = text if str(text).endswith("\n") else f"{text}\n"
    sink = _message_sink.get()
    if sink is not None:
        sink(line)
        return None
    sys.stderr.write(line)
    return None


def capture_output(*exprs, file=None, append=False, type=("output", "message"), split=False):
    kind = match_arg(type, ("output", "message"))
    if len(exprs) != 1:
        raise BackportError("bad argument")
    expr = exprs[0]
    buffer = io.StringIO()
    token = None
    if kind == "message":
        token = _message_sink.set(buffer.write)
    stdout = sys.stdout
    if kind == "output":
        sys.stdout = buffer
    try:
        value = expr() if callable(expr) else expr
        if kind == "output" and value is not None and not callable(expr):
            print(value)
    finally:
        if kind == "output":
            sys.stdout = stdout
        if token is not None:
            _message_sink.reset(token)
    text = buffer.getvalue()
    if split and text:
        stream = sys.stderr if kind == "message" else sys.stdout
        stream.write(text)
    lines = text.splitlines()
    if file is not None:
        mode = "a" if append else "w"
        with open(file, mode, encoding="utf-8") as handle:
            handle.write(text)
    return lines


def get0(x, envir=None, mode="any", inherits=True, ifnotfound=None):
    if isinstance(x, (list, tuple)):
        if len(x) == 0 or any(not isinstance(item, str) for item in x):
            raise BackportError("Invalid first argument")
        if len(x) > 1:
            raise BackportError("first argument has length > 1")
        x = x[0]
    if not isinstance(x, str) or x is NA:
        raise BackportError("Invalid first argument")
    if envir is None:
        frame = sys._getframe(1)
        found, present = _lookup(x, frame.f_locals)
        if not present and inherits:
            found, present = _lookup(x, frame.f_globals)
    else:
        found, present = _lookup(x, envir)
    if not present or not _mode_ok(found, mode):
        return ifnotfound
    return found


def _lookup(name, envir):
    if isinstance(envir, dict):
        if name in envir:
            return envir[name], True
        return None, False
    if hasattr(envir, name):
        return getattr(envir, name), True
    return None, False


def _mode_ok(value, mode) -> bool:
    if mode == "any":
        return True
    if mode == "numeric":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if mode == "character":
        return isinstance(value, str)
    if mode == "logical":
        return isinstance(value, bool)
    if mode == "function":
        return callable(value)
    return True
