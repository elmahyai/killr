"""Delay stdout and conditions while a terminal handler is drawing."""

from __future__ import annotations

import io
import sys
import warnings

from progressr.condition import condition_message, inherits, signal_condition
from progressr.options import ProgressrError, get_option


def _targets(handler):
    env = getattr(handler, "_env", None) or {}
    target = env.get("target", ())
    if isinstance(target, str):
        return (target,)
    return tuple(target)


def _hide_is_null(handler) -> bool:
    env = getattr(handler, "_env", None) or {}
    reporter = env.get("reporter") or {}
    hide = reporter.get("hide")
    if hide is None:
        return True
    return bool(getattr(hide, "null_function", False))


def use_delays(handlers, terminal=None, stdout=None, conditions=None):
    """Decide what to buffer. A target containing 'terminal' delays stdout and conditions."""
    if terminal is None:
        terminal = False
        for handler in handlers:
            if "terminal" in _targets(handler):
                terminal = True
                break
        flush = True
        if terminal:
            flush = True
            for handler in handlers:
                if "terminal" not in _targets(handler):
                    continue
                if _hide_is_null(handler):
                    flush = False
                    break
        terminal = _Flag(bool(terminal), flush=flush)
    else:
        terminal = _Flag(bool(terminal), flush=bool(getattr(terminal, "flush", False)))

    if stdout is None:
        stdout = get_option("progressr.delay_stdout", bool(terminal))
    if conditions is None:
        default = ("condition",) if terminal else ()
        configured = get_option("progressr.delay_conditions", None)
        conditions = default if configured is None else tuple(configured)
    elif isinstance(conditions, str):
        conditions = (conditions,)
    else:
        conditions = tuple(conditions)
    return {"terminal": terminal, "stdout": bool(stdout), "conditions": conditions}


class _Flag:
    """A logical value that also carries R's flush attribute."""

    def __init__(self, value, flush=False):
        self.value = bool(value)
        self.flush = bool(flush)

    def __bool__(self) -> bool:
        return self.value


def buffer_stdout():
    buffer = io.StringIO()
    buffer._prev = sys.stdout
    sys.stdout = buffer
    return buffer


def has_buffered_stdout(stdout_file) -> bool:
    if stdout_file is None:
        return False
    return stdout_file.tell() > 0 or bool(stdout_file.getvalue())


def flush_stdout(stdout_file, close=True, must_work=False):
    """Relay captured stdout. An intermediate flush keeps a trailing partial line."""
    if stdout_file is None:
        return None
    if sys.stdout is not stdout_file:
        if must_work:
            current = 0
            wanted = 1
            raise ProgressrError(
                "[progressr] Cannot flush stdout because the current sink index "
                f"({current}) is out of sync with the sink we want to close ({wanted})"
            )
        return stdout_file
    text = stdout_file.getvalue()
    previous = stdout_file._prev
    sys.stdout = previous
    remainder = ""
    if not close:
        position = text.rfind("\n")
        if position >= 0:
            remainder = text[position + 1 :]
            text = text[: position + 1]
        else:
            remainder = text
            text = ""
    if text:
        previous.write(text)
        previous.flush()
    if not close:
        again = buffer_stdout()
        if remainder:
            again.write(remainder)
        return again
    return None


def flush_conditions(conditions):
    """Relay captured conditions after stdout. Messages go to stderr."""
    pending = list(conditions)
    conditions.clear()
    for condition in pending:
        if inherits(condition, "message"):
            print(condition_message(condition), file=sys.stderr)
        elif inherits(condition, "warning"):
            warnings.warn(condition_message(condition), stacklevel=2)
        elif inherits(condition, "condition"):
            signal_condition(condition)
    return conditions


def delay_stdout(delays, stdout_file):
    if stdout_file is None and delays["stdout"]:
        return buffer_stdout()
    return stdout_file
