"""Numbers and substrings from str2num.R and strfind.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_strings import strTrim
from pracma.util_support import char_list, is_numeric, one_string, require


def str2num(S):
    text = strTrim(S)
    if isinstance(text, list):
        text = text[0]
    show = True
    if text.endswith(";"):
        text = text[:-1]
        show = False
    if text.startswith("["):
        text = text[1:]
    if text.endswith("]"):
        text = text[:-1]
    text = text.replace(",", " ")
    rows = text.split(";")
    parsed = []
    for row in rows:
        tokens = row.split()
        if not tokens:
            parsed.append([])
            continue
        try:
            parsed.append([float(token) for token in tokens])
        except ValueError as exc:
            raise PracmaError("All rows in Argument 's' must have the same length.") from exc
    width = len(parsed[0]) if parsed else 0
    if any(len(row) != width for row in parsed):
        raise PracmaError("All rows in Argument 's' must have the same length.")
    if len(parsed) <= 1:
        values = np.array(parsed[0] if parsed else [], dtype=float)
    else:
        values = np.array(parsed, dtype=float)
    if values.size == 0 or np.any(np.isnan(values)):
        values = None
    if show:
        print(values)
    return values


def num2str(A, fmt=3):
    require(is_numeric(A), "is.numeric(A) is not TRUE")
    require(np.asarray(fmt).size == 1, "length(fmt) == 1 is not TRUE")
    if is_numeric(fmt):
        digits = int(np.round(float(np.asarray(fmt).reshape(-1)[0])))
        pattern = f"%.{digits}f"
    else:
        pattern = str(fmt)
    array = np.asarray(A, dtype=float)
    rendered = [pattern % float(value) for value in array.reshape(-1, order="F")]
    if array.ndim == 2:
        return np.array(rendered, dtype=object).reshape(array.shape, order="F")
    if len(rendered) == 1:
        return rendered[0]
    return rendered


def findstr(s1, s2, overlap=True):
    left = char_list(s1, "is.character(s1) is not TRUE")
    right = char_list(s2, "is.character(s2) is not TRUE")
    if len(left) != 1 or len(right) != 1:
        raise PracmaError("Arguments must be character vectors of length 1.")
    pattern, text = left[0], right[0]
    if len(pattern) > len(text):
        pattern, text = text, pattern
    if pattern == "":
        return None
    width = len(pattern)
    limit = len(text) - width + 1
    found = []
    index = 1
    while index <= limit:
        if pattern == text[index - 1 : index - 1 + width]:
            found.append(float(index))
            if not overlap:
                index += width - 1
        index += 1
    if not found:
        return None
    return np.array(found, dtype=float)


def strfind(s1, s2, overlap=True):
    texts = char_list(s1, "is.character(s1) is not TRUE")
    patterns = char_list(s2, "is.character(s2) is not TRUE")
    if len(patterns) != 1:
        raise PracmaError("Pattern 's2' must be a character vector of length 1.")
    pattern = patterns[0]
    found = []
    for text in texts:
        if len(text) < len(pattern):
            found.append(None)
        else:
            found.append(findstr(pattern, text, overlap=overlap))
    if len(texts) == 1:
        return found[0]
    return found


def strfindi(s1, s2, overlap=True):
    char_list(s1, "is.character(s1) is not TRUE")
    char_list(s2, "is.character(s2) is not TRUE")
    lowered = [item.lower() for item in char_list(s1, "is.character(s1) is not TRUE")]
    pattern = one_string(s2, "is.character(s2) is not TRUE").lower()
    return strfind(lowered if len(lowered) > 1 else lowered[0], pattern, overlap=overlap)
