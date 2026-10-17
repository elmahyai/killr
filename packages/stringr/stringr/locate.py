"""Find where a pattern matches, and turn those spans inside out.

Positions are 1-based inclusive code points, the same indexes stringi
returns. A zero-length match has an end one less than its start.
``str_locate_all`` asks stringi to omit the miss row, so a string with
no match is an empty list of rows.
"""

from __future__ import annotations

from stringi import (
    stri_locate_all_boundaries,
    stri_locate_all_coll,
    stri_locate_all_fixed,
    stri_locate_all_regex,
    stri_locate_first_boundaries,
    stri_locate_first_coll,
    stri_locate_first_fixed,
    stri_locate_first_regex,
)
from stringi._na import NA, is_na

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
    """Copy names when ``pattern`` is length 1 or the same length as ``string``."""

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


def _locate(string: object, pattern: object, all_matches: bool) -> list:
    check_lengths(string, pattern)
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    text = _pattern_text(pattern)
    if kind == "empty" or kind == "bound":
        if all_matches:
            out = stri_locate_all_boundaries(string, omit_no_match=True, opts_brkiter=opts)
        else:
            out = stri_locate_first_boundaries(string, opts_brkiter=opts)
    elif kind == "fixed":
        if all_matches:
            out = stri_locate_all_fixed(string, text, omit_no_match=True, opts_fixed=opts)
        else:
            out = stri_locate_first_fixed(string, text, opts_fixed=opts)
    elif kind == "coll":
        if all_matches:
            out = stri_locate_all_coll(string, text, omit_no_match=True, opts_collator=opts)
        else:
            out = stri_locate_first_coll(string, text, opts_collator=opts)
    elif kind == "regex":
        if all_matches:
            out = stri_locate_all_regex(string, text, omit_no_match=True, opts_regex=opts)
        else:
            out = stri_locate_first_regex(string, text, opts_regex=opts)
    else:
        raise ValueError(f"unknown pattern type {kind}")
    return _preserve(string, pattern, out)


def str_locate(string: object, pattern: object) -> list:
    """Start and end of the first match in each string.

    The result is a list of ``[start, end]`` rows, one row for each
    element of ``string`` or ``pattern``. A miss is ``NA``, ``NA``.
    """

    return _locate(string, pattern, False)


def str_locate_all(string: object, pattern: object) -> list:
    """Start and end of every match.

    The result is a list of location matrices. Each matrix is a list of
    ``[start, end]`` rows. A string with no match contributes an empty list.
    """

    return _locate(string, pattern, True)


def _shift(value: object, delta: int) -> object:
    if is_na(value):
        return NA
    return int(value) + delta


def _location_columns(loc: object) -> tuple[list, list]:
    """Read the start and end columns of a location matrix."""

    if isinstance(loc, dict):
        return list(loc["start"]), list(loc["end"])
    rows = list(loc)
    if not rows:
        return [], []
    if isinstance(rows[0], dict):
        return [row["start"] for row in rows], [row["end"] for row in rows]
    colnames = getattr(loc, "colnames", None)
    if colnames is not None:
        names = list(colnames)
        start_i = names.index("start")
        end_i = names.index("end")
    else:
        start_i, end_i = 0, 1
    return [row[start_i] for row in rows], [row[end_i] for row in rows]


def invert_match(loc: object) -> list:
    """Locations of the gaps between matches.

    ``start`` is ``c(0, end + 1)`` and ``end`` is ``c(start - 1, -1)``,
    the same ``cbind`` as the R function. The result is a list of
    ``[start, end]`` rows. An empty location matrix becomes ``[0, -1]``.
    """

    starts, ends = _location_columns(loc)
    out_start = [0]
    out_end: list = []
    for start, end in zip(starts, ends):
        out_end.append(_shift(start, -1))
        out_start.append(_shift(end, 1))
    out_end.append(-1)
    return [[out_start[i], out_end[i]] for i in range(len(out_start))]
