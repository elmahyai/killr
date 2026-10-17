"""Whitespace trimming for stringr 1.6.0.

``str_trim`` calls the finished stringi trim functions. ``str_squish``
replaces each whitespace run with one space, then trims both sides.
"""

from __future__ import annotations

from stringi import stri_replace_all_regex, stri_trim_both, stri_trim_left, stri_trim_right

from stringr.case import arg_match, as_list, copy_names


def str_trim(string, side="both"):
    """Remove whitespace from the left, the right, or both sides."""

    side = arg_match(side, ("both", "left", "right"), "side")
    if side == "left":
        out = stri_trim_left(string)
    elif side == "right":
        out = stri_trim_right(string)
    else:
        out = stri_trim_both(string)
    return copy_names(string, as_list(out))


def str_squish(string):
    """Trim both sides and collapse internal whitespace to one space."""

    collapsed = as_list(stri_replace_all_regex(string, r"\s+", " ", vectorize_all=True))
    return copy_names(string, stri_trim_both(collapsed))
