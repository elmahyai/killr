"""Minimum-width padding for stringr 1.6.0.

The length check is ``stringr._size.size_common``, the local stand-in for
``vctrs::vec_size_common``. Padding itself is the finished stringi pad
functions. ``use_width=True`` measures display width.
"""

from __future__ import annotations

from stringi import stri_pad_both, stri_pad_left, stri_pad_right

from stringr._size import size_common
from stringr.case import arg_match, as_list, check_bool, copy_names, vector_length


def str_pad(string, width, side="left", pad=" ", use_width=True):
    """Pad each string to ``width``. A longer string is unchanged."""

    size_common(string, width, pad, names=["string", "width", "pad"])
    side = arg_match(side, ("left", "right", "both"), "side")
    check_bool(use_width, "use_width")
    use_length = not use_width
    if side == "left":
        out = stri_pad_left(string, width, pad=pad, use_length=use_length)
    elif side == "right":
        out = stri_pad_right(string, width, pad=pad, use_length=use_length)
    else:
        out = stri_pad_both(string, width, pad=pad, use_length=use_length)
    out = as_list(out)
    if vector_length(string) == len(out):
        return copy_names(string, out)
    return out
