"""like and the %like% family. Patterns follow R's grepl arguments."""

from __future__ import annotations

import re

from datatable._util import DataTableError, as_sequence, is_na


class Factor:
    """A factor: values drawn from levels, matching R's factor indexing."""

    def __init__(self, values, levels=None):
        values = list(values)
        if levels is None:
            levels = sorted({item for item in values if item is not None})
        self.levels = list(levels)
        index = {level: i + 1 for i, level in enumerate(self.levels)}
        self.codes = []
        for item in values:
            if item is None:
                self.codes.append(None)
            elif item not in index:
                raise DataTableError(f"factor level {item!r} is not in levels")
            else:
                self.codes.append(index[item])


def like(vector, pattern, ignore_case=False, fixed=False, perl=False):
    """grepl(pattern, vector). ignore_case, fixed, and perl match the R arguments."""
    del perl  # Python re is the perl-compatible engine used for both modes.
    flags = re.IGNORECASE if ignore_case else 0
    if fixed:
        expression = re.compile(re.escape(str(pattern)), flags)
    else:
        expression = re.compile(str(pattern), flags)
    if isinstance(vector, Factor):
        matched = [bool(expression.search(str(level))) for level in vector.levels]
        out = []
        for code in vector.codes:
            if code is None or code < 1 or code > len(matched):
                out.append(False)
            else:
                out.append(matched[code - 1])
        return out
    values = as_sequence(vector)
    out = []
    for item in values:
        if is_na(item):
            out.append(None)
        else:
            out.append(bool(expression.search(str(item))))
    return out


def like_op(vector, pattern):
    """%like%."""
    return like(vector, pattern)


def ilike(vector, pattern):
    """%ilike%. Case-insensitive grep."""
    return like(vector, pattern, ignore_case=True)


def flike(vector, pattern):
    """%flike%. Fixed pattern, not a regular expression."""
    return like(vector, pattern, fixed=True)


def plike(vector, pattern):
    """%plike%. Perl-compatible regular expression."""
    return like(vector, pattern, perl=True)
