"""Extract the text of a match.

``str_extract`` returns the first match. ``str_extract_all`` returns
every match and, like the R function, omits the miss, so a string with
no match is an empty character vector. ``""`` and ``boundary()`` both
extract boundary segments. A ``group`` argument reads that column of
``str_match``: group 1 is the first capture, which is column 2 in R
and index 1 here.
"""

from __future__ import annotations

from stringi import (
    stri_extract_all_boundaries,
    stri_extract_all_coll,
    stri_extract_all_fixed,
    stri_extract_all_regex,
    stri_extract_first_boundaries,
    stri_extract_first_coll,
    stri_extract_first_fixed,
    stri_extract_first_regex,
)
from stringi._na import is_na

from stringr._size import check_lengths
from stringr.match import str_match
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


def _check_bool(value: object) -> None:
    if value is True or value is False:
        return
    raise ValueError("`TRUE` or `FALSE` is required.")


def _group_indexes(group: object) -> list[int]:
    if isinstance(group, (list, tuple)) and not isinstance(group, str):
        return [_one_group(item) for item in group]
    return [_one_group(group)]


def _one_group(group: object) -> int:
    if isinstance(group, bool) or is_na(group):
        raise TypeError("group must be an integer")
    if isinstance(group, int):
        index = group
    elif isinstance(group, float) and group == int(group):
        index = int(group)
    else:
        raise TypeError("group must be an integer")
    if index < 0:
        raise ValueError("group must be a non-negative integer")
    return index


def _take_groups(matrix: list, indexes: list[int]) -> list:
    """R's ``str_match(...)[, group + 1]`` with ``drop = TRUE``.

    ``group`` is the capture number. Adding one in R selects that column
    of the match matrix, and a dimension of length 1 is dropped. The
    0-based column is therefore ``group`` itself.
    """

    if len(indexes) == 1:
        index = indexes[0]
        return [row[index] for row in matrix]
    if len(matrix) == 1:
        row = matrix[0]
        return [row[index] for index in indexes]
    return [[row[index] for index in indexes] for row in matrix]


def str_extract(string: object, pattern: object, group: object = None) -> list:
    """The first complete match, or one capturing group.

    ``group`` omitted returns the whole match. ``group = 1`` returns the
    first capture. A miss is ``NA``.
    """

    if group is not None:
        matched = str_match(string, pattern)
        return _preserve(string, pattern, _take_groups(matched, _group_indexes(group)))
    check_lengths(string, pattern)
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    text = _pattern_text(pattern)
    if kind == "empty" or kind == "bound":
        out = stri_extract_first_boundaries(string, opts_brkiter=opts)
    elif kind == "fixed":
        out = stri_extract_first_fixed(string, text, opts_fixed=opts)
    elif kind == "coll":
        out = stri_extract_first_coll(string, text, opts_collator=opts)
    elif kind == "regex":
        out = stri_extract_first_regex(string, text, opts_regex=opts)
    else:
        raise ValueError(f"unknown pattern type {kind}")
    return _preserve(string, pattern, out)


def str_extract_all(string: object, pattern: object, simplify: bool = False) -> list:
    """Every match.

    ``simplify = False`` returns a list of character vectors. A miss is
    an empty vector. ``simplify = True`` binds those vectors into a
    character matrix and pads the short rows with empty strings.
    """

    check_lengths(string, pattern)
    _check_bool(simplify)
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    text = _pattern_text(pattern)
    if kind == "empty" or kind == "bound":
        out = stri_extract_all_boundaries(
            string, simplify=simplify, omit_no_match=True, opts_brkiter=opts
        )
    elif kind == "fixed":
        out = stri_extract_all_fixed(
            string, text, simplify=simplify, omit_no_match=True, opts_fixed=opts
        )
    elif kind == "coll":
        out = stri_extract_all_coll(
            string, text, simplify=simplify, omit_no_match=True, opts_collator=opts
        )
    elif kind == "regex":
        out = stri_extract_all_regex(
            string, text, simplify=simplify, omit_no_match=True, opts_regex=opts
        )
    else:
        raise ValueError(f"unknown pattern type {kind}")
    return _preserve(string, pattern, out)
