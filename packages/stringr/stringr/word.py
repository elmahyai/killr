"""Extract a range of words for stringr 1.6.0.

``word`` recycles with ``vctrs.vec_recycle_common``, locates the separator
with the finished stringi locate functions, and slices with ``stri_sub``.
``invert_match`` is the four-line algorithm from ``locate.R``: the
non-match before the first hit starts at 0, and the non-match after the
last hit ends at -1.
"""

from __future__ import annotations

import math

from rlang import Named
from stringi import (
    stri_locate_all_boundaries,
    stri_locate_all_coll,
    stri_locate_all_fixed,
    stri_locate_all_regex,
    stri_sub,
)
from stringi._na import NA, is_na
from vctrs import vec_recycle_common

from stringr._size import check_lengths
from stringr.case import as_list
from stringr.pattern import as_strings, fixed, pattern_opts, pattern_type


def invert_match(loc):
    """Locations of the gaps between matches.

    This is ``cbind(start = c(0L, loc[, "end"] + 1L), end = c(loc[, "start"] - 1L, -1L))``.
    """

    start_col = [0]
    end_col = []
    for row in loc:
        start = row[0]
        end = row[1]
        end_col.append(NA if is_na(start) else start - 1)
        start_col.append(NA if is_na(end) else end + 1)
    end_col.append(-1)
    return [[start_col[i], end_col[i]] for i in range(len(start_col))]


def _locate_all(string, pattern):
    check_lengths(string, pattern)
    kind = pattern_type(pattern)
    options = pattern_opts(pattern)
    values = as_strings(pattern, bare=True)
    if kind in ("empty", "bound"):
        return stri_locate_all_boundaries(
            string, omit_no_match=True, opts_brkiter=options
        )
    if kind == "fixed":
        return stri_locate_all_fixed(
            string, values, omit_no_match=True, opts_fixed=options
        )
    if kind == "coll":
        return stri_locate_all_coll(
            string, values, omit_no_match=True, opts_collator=options
        )
    if kind == "regex":
        return stri_locate_all_regex(
            string, values, omit_no_match=True, opts_regex=options
        )
    raise ValueError("`pattern` must be a character vector.")


def _missing_index(value) -> bool:
    return is_na(value) or (isinstance(value, float) and math.isnan(value))


def _as_index(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(math.trunc(value))
    return int(value)


def _apply_negative(values, lengths):
    out = []
    for value, length in zip(values, lengths):
        if _missing_index(value):
            out.append(NA)
        elif value < 0:
            out.append(value + length + 1)
        else:
            out.append(value)
    return out


def _past_end(values, lengths):
    out = []
    for value, length in zip(values, lengths):
        if _missing_index(value) or value > length:
            out.append(NA)
        else:
            out.append(value)
    return out


def _cell(rows, loc, column):
    """One matrix cell. A zero index is the missing word ``mapply`` produces."""

    if _missing_index(loc):
        return NA
    index = _as_index(loc)
    if index == 0:
        return NA
    if index < 0:
        drop = -index
        kept = [row[column] for number, row in enumerate(rows, start=1) if number != drop]
        if len(kept) == 1:
            return kept[0]
        return NA
    if index > len(rows):
        raise IndexError("subscript out of bounds")
    return rows[index - 1][column]


def _names(source, result):
    names = getattr(source, "names", None)
    if not names:
        return result
    if len(names) == len(result):
        return Named(list(result), list(names))
    if len(names) == 1:
        return Named(list(result), list(names) * len(result))
    return result


def word(string, start=1, end=None, sep=None):
    """Extract words ``start`` through ``end``. A negative index counts from the end."""

    if end is None:
        end = start
    if sep is None:
        sep = fixed(" ")
    string_v, start_v, end_v = vec_recycle_common(string, start, end)
    breaks = _locate_all(string_v, sep)
    words = [invert_match(rows) for rows in breaks]
    lengths = [len(rows) for rows in words]
    start_v = _apply_negative(start_v, lengths)
    end_v = _apply_negative(end_v, lengths)
    start_v = _past_end(start_v, lengths)
    end_v = _past_end(end_v, lengths)
    start_v = [
        1 if (not _missing_index(value) and value < 1) else value for value in start_v
    ]
    starts = [_cell(rows, loc, 0) for rows, loc in zip(words, start_v)]
    ends = [_cell(rows, loc, 1) for rows, loc in zip(words, end_v)]
    out = as_list(stri_sub(string_v, from_=starts, to=ends))
    return _names(string, out)
