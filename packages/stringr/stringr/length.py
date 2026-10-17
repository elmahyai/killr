"""Code-point length and display width.

``str_length`` and ``str_width`` call ``stringi.stri_length`` and
``stringi.stri_width``. A bare string is a length-1 vector, and the
result is always a list. Character ``NA`` is ``stringi._na.NA``.
"""

from __future__ import annotations

from rlang import set_names
from stringi import stri_length, stri_width


def _as_list(value: object) -> list:
    if isinstance(value, list):
        return value
    return [value]


def _copy_names(source: object, out: object) -> list:
    """Copy names from ``source`` when the result has the same length."""

    result = _as_list(out)
    names = getattr(source, "names", None)
    if not names or len(names) != len(result):
        return result
    return set_names(result, list(names))


def str_length(string):
    """Return the number of code points in each string.

    This is ``stringi.stri_length``. Names on ``string`` are kept.
    ``None`` is an empty vector. A bare string has length 1.
    """

    return _copy_names(string, stri_length(string))


def str_width(string):
    """Return the monospaced display width of each string.

    This is ``stringi.stri_width``. Names on ``string`` are kept.
    ``None`` is an empty vector. A bare string has length 1.
    """

    return _copy_names(string, stri_width(string))
