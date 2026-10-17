"""Match counts from stringr 1.6.0.

``""`` and ``boundary()`` count boundaries. Every other pattern is a
regular expression, a fixed string, or a collation, and the option list
comes from :func:`stringr.pattern.pattern_opts`.
"""

from __future__ import annotations

from stringi import (
    stri_count_boundaries,
    stri_count_coll,
    stri_count_fixed,
    stri_count_regex,
    stri_opts_brkiter,
)

from stringr._size import check_lengths
from stringr.detect import _preserve_names
from stringr.pattern import pattern_opts, pattern_type


def str_count(string, pattern=""):
    """How many times ``pattern`` occurs in each element of ``string``.

    The default pattern is the empty string, which counts characters. A
    length-1 argument is recycled, including down to length 0. Names on
    ``string`` are kept when ``pattern`` has length 1 or the same length.
    """

    check_lengths(string, pattern)
    kind = pattern_type(pattern)
    opts = pattern_opts(pattern)
    if kind == "empty" or kind == "bound":
        # pattern_opts knows "" and [""]. A one-element tuple is the same
        # empty pattern, and the empty pattern is a character boundary.
        if kind == "empty" and opts is None:
            opts = stri_opts_brkiter(type="character")
        out = stri_count_boundaries(string, opts_brkiter=opts)
    elif kind == "fixed":
        out = stri_count_fixed(string, pattern, opts_fixed=opts)
    elif kind == "coll":
        out = stri_count_coll(string, pattern, opts_collator=opts)
    elif kind == "regex":
        out = stri_count_regex(string, pattern, opts_regex=opts)
    else:
        raise ValueError(f"unknown pattern type {kind}")
    return _preserve_names(string, pattern, out)
