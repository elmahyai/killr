"""Join words into one string, matching knitr::combine_words."""

from __future__ import annotations

import math
import re

_MISSING = object()


def combine_words(
    words,
    sep=", ",
    and_=" and ",
    before="",
    after=_MISSING,
    oxford_comma=True,
):
    """Combine words into one string.

    ``and_`` is the R argument ``and``. An omitted ``after`` repeats ``before``.
    """

    if after is _MISSING:
        after = before
    return _join(words, sep, and_, before, after, oxford_comma)


def _join(words, sep, and_, before, after, oxford_comma):
    count = _length(words)
    if count == 0:
        return []
    pasted = _paste0(before, words, after)
    if count == 2:
        collapse = sep if _is_blank(and_) else and_
        return _collapse(pasted, collapse)
    if count > 2:
        conjunction = and_
        if oxford_comma and _starts_with_space(and_) and _ends_with_space(sep):
            conjunction = _drop_one_leading_space(and_)
        if len(pasted) < count:
            raise ValueError("subscript out of bounds")
        pasted[count - 1] = _paste_prefix(conjunction, pasted[count - 1])
        if not oxford_comma:
            pasted[count - 2] = pasted[count - 2] + pasted[count - 1]
            del pasted[count - 1]
        return _collapse(pasted, sep)
    if len(pasted) == 1:
        return pasted[0]
    return pasted


def _length(value):
    if value is None:
        return 0
    if isinstance(value, (str, bool, int, float)):
        return 1
    return len(value)


def _elements(value):
    """One R vector. ``None`` is NULL. A string is one element, not characters."""

    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return [value]
    return list(value)


def _paste0(*args):
    parts = []
    for arg in args:
        elements = _elements(arg)
        if not elements:
            continue
        parts.append([_paste_element(item) for item in elements])
    if not parts:
        return []
    width = max(len(part) for part in parts)
    return [
        "".join(part[index % len(part)] for part in parts) for index in range(width)
    ]


def _paste_element(item):
    if item is None:
        return "NA"
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, int) and not isinstance(item, bool):
        return str(item)
    if isinstance(item, float):
        return _paste_double(item)
    if isinstance(item, str):
        return item
    return str(item)


def _paste_double(value):
    """R paste0 of one double: as.character, with scientific notation on a tie."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) <= len(fixed):
        return sci
    return fixed


def _is_blank(value):
    text = _grepl_subject(value)
    if text is None:
        return False
    return re.fullmatch(r"\s*", text) is not None


def _starts_with_space(value):
    text = _grepl_subject(value)
    return text is not None and text.startswith(" ")


def _ends_with_space(value):
    text = _grepl_subject(value)
    return text is not None and text.endswith(" ")


def _grepl_subject(value):
    """The one string grepl sees. NULL in a condition is a missing value."""

    if value is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    elements = _elements(value)
    if not elements:
        raise ValueError("argument is of length zero")
    if len(elements) > 1:
        raise ValueError(f"'length = {len(elements)}' in coercion to 'logical(1)'")
    item = elements[0]
    if item is None:
        return None
    return _paste_element(item)


def _drop_one_leading_space(value):
    text = _grepl_subject(value)
    if text is None:
        return value
    return text[1:]


def _paste_prefix(prefix, word):
    if prefix is None:
        return word
    if isinstance(prefix, str):
        return prefix + word
    return _paste_element(prefix) + word


def _collapse(items, sep):
    if not isinstance(sep, str):
        raise ValueError("invalid 'collapse' argument")
    return sep.join(items)
