"""Return the input filename passed to knit, matching knitr::current_input.

``knit_concord`` holds ``infile``. ``opts_knit`` holds ``output.dir``. Both
are empty when nothing is being knitted, and ``current_input`` then returns
None. On Unix a path that starts with ``/`` or ``~`` is already absolute, so
``dir=True`` returns it unchanged. ``dir=False`` returns the basename, and
that basename expands a leading tilde.
"""

from __future__ import annotations

import math
import os
import warnings


class _OptionStore:
    """Minimal ``new_defaults`` store: get, set, and restore."""

    def __init__(self, initial=None):
        self._initial = dict(initial or {})
        self._values = dict(self._initial)

    def get(self, name):
        return self._values.get(name, None)

    def set(self, **kwargs):
        self._values.update(kwargs)

    def restore(self):
        self._values = dict(self._initial)


knit_concord = _OptionStore(
    {
        "inlines": None,
        "outlines": None,
        "infile": None,
        "outfile": None,
        "block": None,
        "offset": None,
    }
)

opts_knit = _OptionStore()


def current_input(dir=False):
    """Name of the file passed to knit.

    ``dir=False`` returns the basename. ``dir=True`` returns an absolute
    path, or the path under ``output.dir`` when the input is relative. With
    no input file, the result is None and ``dir`` is not examined.
    """

    text = knit_concord.get("infile")
    outwd = opts_knit.get("output.dir")
    if text is None:
        return None
    use_dir = _condition(dir)
    if use_dir and outwd is None:
        warnings.warn(
            "Cannot determine the directory of the input document",
            stacklevel=2,
        )
        use_dir = False
    if not use_dir:
        return _basename(text)
    if _is_abs_path(text):
        return text
    return f"{outwd}/{text}"


def _condition(value):
    """R's ``if (dir)`` on one already-evaluated value."""

    if value is None:
        raise ValueError("argument is of length zero")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError("missing value where TRUE/FALSE needed")
        return value != 0.0
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        if len(value) > 1:
            raise ValueError("the condition has length > 1")
        return _condition(value[0])
    raise ValueError("invalid argument type")


def _is_abs_path(text):
    """xfun::is_abs_path on Unix: a leading ``/`` or ``~``."""

    if not isinstance(text, str):
        raise ValueError("missing value where TRUE/FALSE needed")
    return text.startswith("/") or text.startswith("~")


def _basename(text):
    """R's ``basename``: expand a leading tilde, then drop trailing slashes."""

    if not isinstance(text, str):
        raise TypeError("basename expects a character string")
    expanded = os.path.expanduser(text)
    trimmed = expanded.rstrip("/")
    if trimmed == "":
        return ""
    slash = trimmed.rfind("/")
    if slash < 0:
        return trimmed
    return trimmed[slash + 1 :]
