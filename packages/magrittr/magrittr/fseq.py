"""Functional-sequence helpers from magrittr.

FSeq lives in magrittr._fseq. This module does not define it again.
"""

from __future__ import annotations

import inspect
import math

from magrittr._fseq import FSeq

_DEBUG_ATTR = "_magrittr_debugged"
_DEBUGGED_IDS: set[int] = set()


def freduce(value, function_list):
    """Apply each function in ``function_list`` to ``value`` in turn."""
    steps = list(function_list)
    k = len(steps)
    if k > 1:
        for fn in steps[:-1]:
            value = fn(value)
    if k < 1:
        raise IndexError(
            "attempt to select less than one element in integerOneIndex"
        )
    return steps[k - 1](value)


def functions(fseq):
    """Return the function list stored on a functional sequence."""
    if not isinstance(fseq, FSeq):
        raise ValueError("Object is not a functional sequence.")
    return fseq._function_list


def debug_pipe(x):
    """Print the batch browser lines and return ``x``."""
    print(f"Called from: {_called_from(x)}", flush=True)
    print("debug: x", flush=True)
    return x


def debug_fseq(fseq, *indices):
    """Mark the selected functions. Return None, or reject invalid indices."""
    numeric = [_is_numeric(index) for index in indices]
    if not any(numeric):
        raise ValueError("Index or indices invalid.")
    steps = functions(fseq)
    n = len(steps)
    valid = [_is_valid_index(index, n) for index in indices]
    if not any(valid):
        raise ValueError("Index or indices invalid.")
    for index in indices:
        _mark(_select(steps, index))
    return None


def undebug_fseq(fseq):
    """Clear debug marks on every function in the sequence."""
    for fn in functions(fseq):
        if _is_debugged(fn):
            _unmark(fn)
    return None


def _is_debugged(fn) -> bool:
    if getattr(fn, _DEBUG_ATTR, False):
        return True
    return id(fn) in _DEBUGGED_IDS


def _mark(fn) -> None:
    try:
        setattr(fn, _DEBUG_ATTR, True)
    except (AttributeError, TypeError):
        _DEBUGGED_IDS.add(id(fn))


def _unmark(fn) -> None:
    try:
        if hasattr(fn, _DEBUG_ATTR):
            setattr(fn, _DEBUG_ATTR, False)
    except (AttributeError, TypeError):
        pass
    _DEBUGGED_IDS.discard(id(fn))


def _is_numeric(index) -> bool:
    if isinstance(index, bool):
        return False
    return isinstance(index, (int, float))


def _is_valid_index(index, n: int) -> bool:
    if isinstance(index, (list, tuple)):
        raise ValueError(
            "values must be length 1,\n"
            f" but FUN(X[[1]]) result is length {len(index)}"
        )
    if isinstance(index, bool):
        return bool(index) and n >= 1
    if isinstance(index, (int, float)):
        if isinstance(index, float) and math.isnan(index):
            return False
        return any(index == position for position in range(1, n + 1))
    if isinstance(index, str):
        try:
            number = float(index)
        except ValueError:
            return False
        if math.isnan(number):
            return False
        return any(number == position for position in range(1, n + 1))
    return False


def _select(steps, index):
    if isinstance(index, str) or index is None:
        raise ValueError("argument must be a function")
    if isinstance(index, bool):
        number = 1.0 if index else 0.0
    elif isinstance(index, (int, float)):
        if isinstance(index, float) and math.isnan(index):
            raise ValueError("argument must be a function")
        number = float(index)
    else:
        raise ValueError("argument must be a function")
    truncated = math.trunc(number)
    if truncated == 0:
        raise IndexError(
            "attempt to select less than one element in get1index <real>"
        )
    if truncated < 0:
        raise IndexError("invalid negative subscript in get1index <real>")
    if truncated > len(steps):
        raise IndexError("subscript out of bounds")
    return steps[truncated - 1]


def _called_from(argument) -> str:
    frame = inspect.currentframe()
    caller = None
    if frame is not None and frame.f_back is not None:
        caller = frame.f_back.f_back
    line = ""
    if caller is not None:
        try:
            info = inspect.getframeinfo(caller, context=1)
            if info.code_context:
                line = info.code_context[0]
        except OSError:
            line = ""
    extracted = _extract_call(line)
    if extracted:
        return extracted
    return f"debug_pipe({_fallback_arg(argument)})"


def _extract_call(line: str) -> str | None:
    start = line.find("debug_pipe")
    if start < 0:
        return None
    rest = line[start:]
    cursor = len("debug_pipe")
    while cursor < len(rest) and rest[cursor].isspace():
        cursor += 1
    if cursor >= len(rest) or rest[cursor] != "(":
        return None
    depth = 0
    for index in range(cursor, len(rest)):
        char = rest[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return rest[: index + 1]
    return None


def _fallback_arg(argument) -> str:
    if isinstance(argument, str):
        return '"' + argument.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(argument, bool):
        return "TRUE" if argument else "FALSE"
    if isinstance(argument, int) and not isinstance(argument, bool):
        return str(argument)
    return repr(argument)
