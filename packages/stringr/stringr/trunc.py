"""Maximum-width truncation for stringr 1.6.0.

``str_trunc`` measures with ``stri_length`` and slices with ``stri_sub``.
The pieces are joined with ``stri_c``. Width and the ellipsis are single
values; the string is a vector.
"""

from __future__ import annotations

import math

from stringi import stri_c, stri_length, stri_sub
from stringi._na import is_na

from stringr.case import (
    arg_match,
    as_list,
    check_number_whole,
    check_string,
    copy_names,
)


def _texts(string) -> list:
    if string is None:
        return []
    if is_na(string) or isinstance(string, str):
        return [string]
    if isinstance(string, (list, tuple)):
        return list(string)
    raise TypeError("`string` must be a character vector.")


def _one_length(value) -> int:
    result = stri_length(value)
    if isinstance(result, list):
        result = result[0]
    if is_na(result):
        raise ValueError("`ellipsis` must be a single string.")
    return int(result)


def str_trunc(string, width, side="right", ellipsis="..."):
    """Shorten strings that are longer than ``width``, adding ``ellipsis``."""

    check_number_whole(width, "width")
    side = arg_match(side, ("right", "left", "center"), "side")
    check_string(ellipsis, "ellipsis")
    width_i = int(width)
    ellipsis_n = _one_length(ellipsis)
    rest = width_i - ellipsis_n
    if rest < 0:
        raise ValueError(
            f"`width` ({width_i}) is shorter than `ellipsis` ({ellipsis_n})."
        )
    texts = _texts(string)
    lengths = as_list(stri_length(texts))
    too_long = [
        (not is_na(text)) and (not is_na(n)) and n > width_i
        for text, n in zip(texts, lengths)
    ]
    if not any(too_long):
        return copy_names(string, texts)
    chosen = [texts[i] for i, flag in enumerate(too_long) if flag]
    chosen_n = [int(lengths[i]) for i, flag in enumerate(too_long) if flag]
    if side == "right":
        parts = as_list(stri_sub(chosen, from_=1, to=rest))
        replacement = as_list(stri_c(parts, ellipsis))
    elif side == "left":
        starts = [n - rest + 1 for n in chosen_n]
        parts = as_list(stri_sub(chosen, from_=starts, to=-1))
        replacement = as_list(stri_c(ellipsis, parts))
    else:
        left_n = math.ceil(rest / 2)
        right_n = math.floor(rest / 2)
        left = as_list(stri_sub(chosen, from_=1, to=left_n))
        starts = [n - right_n + 1 for n in chosen_n]
        right = as_list(stri_sub(chosen, from_=starts, to=-1))
        replacement = as_list(stri_c(left, ellipsis, right))
    out = list(texts)
    cursor = 0
    for index, flag in enumerate(too_long):
        if flag:
            out[index] = replacement[cursor]
            cursor += 1
    return copy_names(string, out)
