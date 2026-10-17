"""List-to-matrix and missing-value helpers from stringi.

A character vector is a list. A missing character is ``stringi._na.NA``.
An empty string is empty; a missing character is not.
"""

from __future__ import annotations

import warnings

from stringi._na import NA, is_na


def _coerce_scalar(value):
    if is_na(value):
        return NA
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    raise TypeError(
        "argument should be a character vector (or an integer, logical, or missing value)"
    )


def _as_character(x):
    if isinstance(x, (list, tuple)):
        return [_coerce_scalar(item) for item in x]
    return [_coerce_scalar(x)]


def _first(value, name, kind):
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single {kind}; "
                "only the first element is used",
                stacklevel=3,
            )
        return value[0]
    return value


def _as_one_string(value, name):
    return _coerce_scalar(_first(value, name, "character string"))


def _as_bool(value, name):
    value = _first(value, name, "logical value")
    if is_na(value):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value == value and value not in (
        float("inf"),
        float("-inf"),
    ):
        return value != 0
    raise TypeError(f"argument `{name}` should be a single logical value")


def _as_n_min(value):
    value = _first(value, "n_min", "integer value")
    if is_na(value):
        raise ValueError("missing values in argument `n_min` is not supported")
    if isinstance(value, bool):
        number = int(value)
    elif isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(
                "incorrect argument `n_min`; expected a nonnegative numeric value"
            )
        number = int(value)
    else:
        raise TypeError("argument `n_min` should be a single integer value")
    if number < 0:
        raise ValueError(
            "incorrect argument `n_min`; expected a nonnegative numeric value"
        )
    return number


def _as_atomic(item):
    if isinstance(item, (list, tuple)):
        return [_coerce_scalar(value) for value in item]
    return [_coerce_scalar(item)]


def _is_empty(value):
    """An empty string is empty. A missing character is not."""
    if is_na(value):
        return False
    return value == ""


def stri_list2matrix(x, byrow=False, fill=NA, n_min=0, by_row=None):
    """Convert a list of atomic vectors to a character matrix.

    The result is a list of rows, in the order R prints the matrix.
    Each inner list is one row from left to right. With ``byrow`` false,
    column ``j`` is ``x[j]`` padded with ``fill``. With ``byrow`` true,
    that matrix is transposed. ``by_row`` overrides ``byrow`` when it is
    not None. ``n_min`` is the minimum number of rows, or of columns when
    ``byrow`` is true.
    """
    if by_row is not None:
        byrow = by_row
    byrow = _as_bool(byrow, "byrow")
    pad = _as_one_string(fill, "fill")
    height = _as_n_min(n_min)
    if isinstance(x, (str, bytes)) or is_na(x) or not isinstance(x, (list, tuple)):
        raise TypeError(
            "argument `x` should be a list of character vectors "
            "(or an object coercible to)"
        )
    vectors = [_as_atomic(item) for item in x]
    n = len(vectors)
    m = height
    for vector in vectors:
        if len(vector) > m:
            m = len(vector)
    if not byrow:
        return [
            [vectors[j][i] if i < len(vectors[j]) else pad for j in range(n)]
            for i in range(m)
        ]
    return [
        [vectors[i][j] if j < len(vectors[i]) else pad for j in range(m)]
        for i in range(n)
    ]


def stri_na2empty(x):
    """Replace missing characters with empty strings."""
    return ["" if is_na(value) else value for value in _as_character(x)]


def stri_remove_empty(x, na_empty=False):
    """Drop empty strings. Drop missing values only when ``na_empty`` is True.

    ``na_empty`` follows R's ``identical(na_empty, TRUE)``: only the boolean
    True removes missing values. An empty string is empty. NA is not empty,
    so it stays unless that flag is True.
    """
    drop_na = na_empty is True
    kept = []
    for value in _as_character(x):
        if _is_empty(value):
            continue
        if drop_na and is_na(value):
            continue
        kept.append(value)
    return kept


stri_omit_empty = stri_remove_empty


def stri_remove_empty_na(x):
    """Drop empty strings and missing values."""
    return stri_remove_empty(x, True)


stri_omit_empty_na = stri_remove_empty_na


def stri_remove_na(x):
    """Drop missing values and keep empty strings."""
    return [value for value in _as_character(x) if not is_na(value)]


stri_omit_na = stri_remove_na


def stri_replace_na(str, replacement="NA"):
    """Replace each missing character with ``replacement``.

    The default replacement is the string ``"NA"``, not a missing value.
    A missing replacement leaves missing values missing.
    """
    repl = _as_one_string(replacement, "replacement")
    return [repl if is_na(value) else value for value in _as_character(str)]
