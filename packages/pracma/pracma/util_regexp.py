"""Regular expressions from pracma regexp.R."""

from __future__ import annotations

import re
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import char_list, require, whole_number


def _first_string(value, label):
    require(isinstance(value, str) or (
        isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value)
    ), f"is.character({label}) is not TRUE")
    items = char_list(value, f"is.character({label}) is not TRUE")
    if any(item is None for item in items):
        raise PracmaError("In arguments 'pat' and 's' NA values not allowed.")
    if len(items) > 1:
        warnings.warn(f"Only the first string in argument '{label}' is taken.", stacklevel=3)
    return items[0]


def regexp(s, pat, ignorecase=False, once=False, split=False):
    pattern = _first_string(pat, "pat")
    text = _first_string(s, "s")
    flags = re.IGNORECASE if ignorecase else 0
    if once:
        found = re.search(pattern, text, flags=flags)
        matches = [] if found is None else [found]
    else:
        matches = list(re.finditer(pattern, text, flags=flags))
    if not matches:
        return {
            "start": None,
            "end": None,
            "match": None,
            "split": text if split else None,
        }
    starts = [match.start() + 1 for match in matches]
    ends = [match.end() for match in matches]
    pieces = [match.group(0) for match in matches]
    parts = None
    if split:
        n = len(text)
        rs = [0, *starts, n + 1]
        re_ = [0, *ends, n + 1]
        parts = []
        for index in range(len(rs) - 1):
            if rs[index + 1] - re_[index] > 1:
                parts.append(text[re_[index] : rs[index + 1] - 1])
    return {
        "start": np.array(starts, dtype=float),
        "end": np.array(ends, dtype=float),
        "match": pieces[0] if len(pieces) == 1 else pieces,
        "split": parts,
    }


def regexpi(s, pat, once=False, split=False):
    return regexp(s, pat, ignorecase=True, once=once, split=split)


def regexprep(s, expr, repstr, ignorecase=False, once=False):
    items = char_list(s, "Argument 's' must be a character vector.")
    patterns = char_list(expr, "Arguments 'old' and 'new' must be simple character strings.")
    replacements = char_list(repstr, "Arguments 'old' and 'new' must be simple character strings.")
    if len(patterns) != 1 or len(replacements) != 1:
        raise PracmaError("Arguments 'old' and 'new' must be simple character strings.")
    flags = re.IGNORECASE if ignorecase else 0
    count = 1 if once else 0
    replaced = [
        re.sub(patterns[0], replacements[0], item, count=count, flags=flags) for item in items
    ]
    if len(replaced) == 1:
        return replaced[0]
    return replaced


def refindall(s, pat, over=1, ignorecase=False):
    texts = char_list(s, "Arguments 's' and 'pat' must be single strings.")
    patterns = char_list(pat, "Arguments 's' and 'pat' must be single strings.")
    if len(texts) != 1 or len(patterns) != 1:
        raise PracmaError("Arguments 's' and 'pat' must be single strings.")
    require(
        not isinstance(over, (bool, np.bool_)) and _numeric_scalar(over),
        "Argument 'over' must be a positive integer.",
    )
    step = float(np.asarray(over).reshape(-1)[0])
    if np.asarray(over).size != 1 or step < 1 or not whole_number(step):
        raise PracmaError("Argument 'over' must be a positive integer.")
    text = texts[0]
    pattern = patterns[0]
    flags = re.IGNORECASE if ignorecase else 0
    positions = []
    index = 1
    length = len(text)
    while index <= length:
        found = re.search(pattern, text[index - 1 :], flags=flags)
        if found is None:
            break
        at = found.start() + 1
        positions.append(index + at - 1)
        index = index + at + (int(step) - 1)
    if not positions:
        return None
    return np.array(positions, dtype=float)


def _numeric_scalar(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    array = np.asarray(value)
    return array.size == 1 and array.dtype != object and np.issubdtype(array.dtype, np.number)
