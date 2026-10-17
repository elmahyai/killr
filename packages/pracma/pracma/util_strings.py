"""Character helpers from pracma strings.R."""

from __future__ import annotations

import re

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import char_list, match_arg, require


def blanks(n=1):
    require(not isinstance(n, (bool, np.bool_)) and _is_number(n), "is.numeric(n) is not TRUE")
    require(np.asarray(n).size == 1, "length(n) == 1 is not TRUE")
    number = float(np.asarray(n).reshape(-1)[0])
    require(number >= 0, "n >= 0 is not TRUE")
    return " " * int(np.floor(number))


def _is_number(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    array = np.asarray(value)
    return array.dtype != object and array.dtype != bool and np.issubdtype(array.dtype, np.number)


def strcat(s1, s2=None, collapse=""):
    require(isinstance(collapse, str), "is.character(collapse) is not TRUE")
    left = char_list(s1, "Argument 's1' must be a character vector.")
    if s2 is None:
        return collapse.join(left)
    right = char_list(s2, "Argument 's2' must be a character vector.")
    expanded = [item for item in left for _ in right]
    tiled = (right * ((len(expanded) + len(right) - 1) // len(right)))[: len(expanded)]
    pasted = [collapse.join((one, two)) for one, two in zip(expanded, tiled)]
    if len(pasted) == 1:
        return pasted[0]
    return pasted


def _compare_chars(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, (bool, np.bool_)):
        return ["TRUE" if bool(value) else "FALSE"]
    if isinstance(value, (list, tuple, np.ndarray)):
        items = []
        for item in np.asarray(value, dtype=object).reshape(-1):
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, (bool, np.bool_)):
                items.append("TRUE" if bool(item) else "FALSE")
            else:
                items.append(str(item))
        return items
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
        return [str(value) if not float(value).is_integer() else str(int(value))]
    return [str(value)]


def strcmp(s1, s2):
    # The installed source tests s1 twice, so s2 is not required to be character.
    try:
        char_list(s1, "Arguments 's1' and 's2' must be character vectors.")
    except PracmaError:
        raise
    left = char_list(s1, "Arguments 's1' and 's2' must be character vectors.")
    right = _compare_chars(s2)
    if len(left) != len(right):
        return False
    return all(one == two for one, two in zip(left, right))


def strcmpi(s1, s2):
    try:
        char_list(s1, "Arguments 's1' and 's2' must be character vectors.")
    except PracmaError:
        raise
    left = [item.lower() for item in char_list(s1, "Arguments 's1' and 's2' must be character vectors.")]
    right = [item.lower() for item in _compare_chars(s2)]
    return strcmp(left, right)


def _trim_one(text: str) -> str:
    return re.sub(r"\s+$", "", re.sub(r"^\s+", "", text))


def _maybe_one(items):
    if len(items) == 1:
        return items[0]
    return items


def strTrim(s):
    items = char_list(s, "Argument 's' must be a character vector.")
    return _maybe_one([_trim_one(item) for item in items])


def deblank(s):
    items = char_list(s, "Argument 's' must be a character vector.")
    return _maybe_one([re.sub(r"\s+$", "", item) for item in items])


def strjust(s, justify="left"):
    items = [_trim_one(item) for item in char_list(s, "Argument 's' must be a character vector.")]
    justify = match_arg(justify, ("left", "right", "center"))
    if not items:
        return []
    width = max(len(item) for item in items)
    padded = []
    for item in items:
        gap = width - len(item)
        if justify == "left":
            padded.append(item + blanks(gap))
        elif justify == "right":
            padded.append(blanks(gap) + item)
        else:
            left = gap // 2
            right = gap - left
            padded.append(blanks(left) + item + blanks(right))
    return _maybe_one(padded)


def strRep(s, old, new):
    items = char_list(s, "Argument 's' must be a character vector.")
    old_items = char_list(old, "Arguments 'old' and 'new' must be simple character strings.")
    new_items = char_list(new, "Arguments 'old' and 'new' must be simple character strings.")
    if len(old_items) != 1 or len(new_items) != 1:
        raise PracmaError("Arguments 'old' and 'new' must be simple character strings.")
    replaced = [item.replace(old_items[0], new_items[0]) for item in items]
    return _maybe_one(replaced)
