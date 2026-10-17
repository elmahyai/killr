"""Extract a match and its capture groups.

Only a regular expression is accepted. A plain string is a regular
expression. ``fixed``, ``coll``, ``boundary``, and ``""`` are not.
Missing groups are :data:`stringi._na.NA`. ``str_match_all`` omits the
miss row, so a string with no match is a matrix with no rows.
"""

from __future__ import annotations

from stringi import stri_match_all_regex, stri_match_first_regex
from stringi._na import is_na

from stringr._size import check_lengths
from stringr.pattern import pattern_opts, pattern_type


class _Named(list):
    """A vector or matrix that keeps the names of ``string``."""

    def __init__(self, items, names=None, colnames=None):
        super().__init__(items)
        self.names = names
        self.colnames = colnames


def _length(value: object) -> int:
    if isinstance(value, (str, bytes)) or is_na(value) or isinstance(value, (bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    raise TypeError(f"cannot take the size of {type(value).__name__}")


def _pattern_text(pattern: object) -> object:
    if isinstance(pattern, (str, bytes)) or is_na(pattern):
        return pattern
    return list(pattern)


def _preserve(string: object, pattern: object, out: list) -> list:
    names = getattr(string, "names", None)
    if names is None:
        return out
    if _length(pattern) != 1 and _length(pattern) != _length(string):
        return out
    wrapped = _Named(list(out), names=list(names))
    colnames = getattr(out, "colnames", None)
    if colnames is not None:
        wrapped.colnames = list(colnames)
    return wrapped


def _require_regex(pattern: object) -> None:
    if pattern_type(pattern) != "regex":
        raise ValueError("`pattern` must be a regular expression.")


def str_match(string: object, pattern: object) -> list:
    """The first match and its capture groups.

    Each row is one string. Column 0 is the whole match. Later columns
    are the capturing groups, and a group that did not participate is
    ``NA``. Named groups are stored on ``colnames`` when ``pattern`` is
    a single pattern. The first column name is empty.
    """

    check_lengths(string, pattern)
    _require_regex(pattern)
    out = stri_match_first_regex(string, _pattern_text(pattern), opts_regex=pattern_opts(pattern))
    return _preserve(string, pattern, out)


def str_match_all(string: object, pattern: object) -> list:
    """Every match and its capture groups.

    Each element is a character matrix with one row per match. A miss is
    a matrix with no rows. A missing string is one row of ``NA``.
    """

    check_lengths(string, pattern)
    _require_regex(pattern)
    out = stri_match_all_regex(
        string,
        _pattern_text(pattern),
        omit_no_match=True,
        opts_regex=pattern_opts(pattern),
    )
    return _preserve(string, pattern, out)
