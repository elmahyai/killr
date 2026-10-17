"""The ... helpers. The caller stores a Dots sequence in _dots."""

from __future__ import annotations

import sys

from backports._values import BackportError

__all__ = ["Dots", "dots_elt", "dots_length", "dots_names"]

_MISSING_DOTS = "incorrect context: the current call has no '...' to look in"


class Dots(tuple):
    """Pairs of (name, value). An unnamed argument uses ""."""

    def __new__(cls, *pairs):
        cleaned = []
        for pair in pairs:
            if len(pair) != 2:
                raise BackportError("each dots entry is a name and a value")
            name, value = pair
            cleaned.append((name or "", value))
        return super().__new__(cls, cleaned)


def dots_length():
    return len(_require())


def dots_elt(n):
    dots = _require()
    index = int(n)
    if index <= 0:
        raise BackportError(f"indexing '...' with non-positive index {index}")
    if index > len(dots):
        raise BackportError(f"the ... list does not contain {index} elements")
    return dots[index - 1][1]


def dots_names():
    dots = _require()
    if not any(name for name, _value in dots):
        return None
    return [name for name, _value in dots]


def _require() -> Dots:
    frame = sys._getframe(2)
    if "_dots" not in frame.f_locals or not isinstance(frame.f_locals["_dots"], Dots):
        raise BackportError(_MISSING_DOTS)
    return frame.f_locals["_dots"]
