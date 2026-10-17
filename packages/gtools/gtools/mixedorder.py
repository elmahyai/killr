"""Mixed sort order for strings with embedded numbers (gtools 3.9.5 ``mixedorder``)."""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np

_DELIM = "$@$"
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

_DECIMAL_SCI_REGEX = re.compile(
    r"((?:[-+]?)(?:(?=[.]?[0123456789])(?:[0123456789]*)(?:(?:[.])(?:[0123456789]{0,}))?)"
    r"(?:(?:[eE])(?:(?:[-+]?)(?:[0123456789]+))|))",
    re.IGNORECASE,
)
_DECIMAL_REGEX = re.compile(
    r"((?:[-+]?)(?:(?=[.]?[0123456789])(?:[0123456789]*)(?:(?:[.])(?:[0123456789]{0,}))?))",
    re.IGNORECASE,
)
_ROMAN_BOTH_REGEX = re.compile(r"([IVXCLDMivxcldm]+)")
_ROMAN_UPPER_REGEX = re.compile(r"([IVXCLDM]+)")
_ROMAN_LOWER_REGEX = re.compile(r"([ivxcldm]+)")


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"'{value}' is not one of {', '.join(repr(c) for c in choices)}")
    return value


def _roman2int(text: str) -> float:
    text = text.strip().upper()
    if not text:
        return np.nan
    try:
        values = [_ROMAN_VALUES[ch] for ch in text]
    except KeyError:
        return np.nan
    total = 0
    if len(values) > 1:
        for index in range(len(values) - 1):
            if values[index] < values[index + 1]:
                total -= values[index]
            else:
                total += values[index]
    total += values[-1]
    return float(total)


def _is_character(x) -> bool:
    if isinstance(x, str):
        return True
    if isinstance(x, np.ndarray):
        return x.dtype.kind in {"U", "S"}
    if isinstance(x, Sequence) and not isinstance(x, (bytes, bytearray)):
        return all(item is None or isinstance(item, str) for item in x)
    return False


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_vals = values[order]
    positions = np.arange(1, len(values) + 1, dtype=float)
    ranks = np.empty(len(values), dtype=float)
    tied = np.concatenate(([False], sorted_vals[1:] == sorted_vals[:-1]))
    start = 0
    for index in range(1, len(sorted_vals) + 1):
        if index == len(sorted_vals) or not tied[index]:
            avg = positions[start:index].mean()
            ranks[order[start:index]] = avg
            start = index
    return ranks


def _r_rank(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    ranks = np.full(n, np.nan, dtype=float)
    finite = ~np.isnan(arr)
    next_rank = 1.0
    if finite.any():
        finite_ranks = _average_ranks(arr[finite])
        ranks[finite] = finite_ranks
        next_rank = float(np.max(finite_ranks)) + 1.0
    na_positions = np.flatnonzero(np.isnan(arr))
    for offset, position in enumerate(na_positions):
        ranks[position] = next_rank + offset
    return ranks


def _r_factor_numeric(values: list[str | float]) -> np.ndarray:
    labels: list[str | None] = []
    for value in values:
        if isinstance(value, float) and np.isnan(value):
            labels.append(None)
        else:
            labels.append(str(value))
    unique = sorted({label for label in labels if label is not None})
    mapping = {label: float(index + 1) for index, label in enumerate(unique)}
    ranks = np.full(len(labels), np.nan, dtype=float)
    for index, label in enumerate(labels):
        if label is not None:
            ranks[index] = mapping[label]
    return ranks


def _r_order(*columns: np.ndarray, decreasing: bool = False, na_last: bool | None = True) -> np.ndarray:
    n = len(columns[0])
    if n == 0:
        return np.array([], dtype=np.int64)
    keep = np.ones(n, dtype=bool)
    if na_last is None:
        for column in columns:
            keep &= ~np.isnan(column)
        if not keep.any():
            return np.array([], dtype=np.int64)
    sort_keys: list[np.ndarray] = []
    if na_last is not None:
        na_key = np.zeros(n, dtype=float)
        for column in columns:
            if na_last:
                na_key += np.where(np.isnan(column), 1.0, 0.0)
            else:
                na_key += np.where(np.isnan(column), 0.0, 1.0)
        sort_keys.append(na_key)
    for column in reversed(columns):
        key = np.array(column, dtype=float, copy=True)
        if na_last is None:
            key = key[keep]
        if decreasing:
            key = -key
        sort_keys.append(key)
    if na_last is None:
        order = np.lexsort(tuple(sort_keys))
        return np.flatnonzero(keep)[order] + 1
    order = np.lexsort(tuple(sort_keys))
    return order + 1


def mixedorder(
    x,
    decreasing: bool = False,
    na_last: bool | None = True,
    blank_last: bool | None = False,
    numeric_type: str = "decimal",
    roman_case: str = "upper",
    scientific: bool = True,
):
    """Return the sort order for strings with embedded numeric sections."""
    numeric_type = _match_arg(numeric_type, ("decimal", "roman"))
    roman_case = _match_arg(roman_case, ("upper", "lower", "both"))

    if isinstance(x, np.ndarray) and x.ndim == 0:
        x = x.item()

    if isinstance(x, str):
        length = 1
    elif isinstance(x, np.ndarray):
        length = x.size
    else:
        length = len(x)

    if length < 1:
        return None
    if length == 1:
        return np.array([1], dtype=np.int64)

    if not _is_character(x):
        if isinstance(x, np.ndarray):
            arr = np.ravel(x, order="F").astype(float)
        else:
            arr = np.asarray(list(x), dtype=float)
        return _r_order(arr, decreasing=decreasing, na_last=na_last)

    if isinstance(x, str):
        items = [x]
    elif isinstance(x, np.ndarray):
        items = [None if item is None else str(item) for item in x.ravel(order="F")]
    else:
        items = list(x)

    if numeric_type == "decimal":
        regex = _DECIMAL_SCI_REGEX if scientific else _DECIMAL_REGEX

        def numeric_fn(token: str) -> float:
            with np.errstate(all="ignore"):
                try:
                    return float(token)
                except ValueError:
                    return np.nan

    else:
        if roman_case == "both":
            regex = _ROMAN_BOTH_REGEX
        elif roman_case == "upper":
            regex = _ROMAN_UPPER_REGEX
        else:
            regex = _ROMAN_LOWER_REGEX

        def numeric_fn(token: str) -> float:
            return _roman2int(token)

    def nonnumeric_fn(token: str) -> str | float:
        value = numeric_fn(token)
        if np.isnan(value):
            return token.upper()
        return np.nan

    na_mask = np.array(
        [item is None or (isinstance(item, float) and np.isnan(item)) for item in items],
        dtype=bool,
    )
    which_nas = np.flatnonzero(na_mask)
    texts: list[str | None] = []
    for item in items:
        if item is None or (isinstance(item, float) and np.isnan(item)):
            texts.append(None)
        else:
            texts.append(str(item))
    which_blanks = np.array([index for index, text in enumerate(texts) if text == ""], dtype=np.int64)

    step1_numeric: list[list[float]] = []
    step1_character: list[list[str | float]] = []
    for text in texts:
        if text is None:
            step1_numeric.append([])
            step1_character.append([])
            continue
        delimited = regex.sub(f"{_DELIM}\\1{_DELIM}", text)
        parts = [part for part in delimited.split(_DELIM) if part > ""]
        nums: list[float] = []
        chars: list[str | float] = []
        for part in parts:
            nums.append(numeric_fn(part))
            chars.append(nonnumeric_fn(part))
        step1_numeric.append(nums)
        step1_character.append(chars)

    maxelem = max((len(parts) for parts in step1_numeric), default=0)
    if maxelem == 0:
        rank_overall = np.empty((len(items), 0), dtype=float)
    else:
        step1_numeric_t = [
            [row[index] if index < len(row) else np.nan for row in step1_numeric]
            for index in range(maxelem)
        ]
        step1_character_t = [
            [row[index] if index < len(row) else np.nan for row in step1_character]
            for index in range(maxelem)
        ]

        rank_numeric = np.column_stack([_r_rank(column) for column in step1_numeric_t])
        rank_character = np.column_stack([_r_factor_numeric(column) for column in step1_character_t])

        mask = ~np.isnan(rank_character)
        rank_numeric = rank_numeric.copy()
        rank_numeric[mask] = 0.0

        col_max = np.nanmax(rank_numeric, axis=0)
        col_max = np.where(np.isfinite(col_max), col_max, 0.0)
        rank_character = rank_character + col_max

        rank_overall = np.where(np.isnan(rank_character), rank_numeric, rank_character)

    frame = np.array(rank_overall, dtype=float, copy=True)
    if which_nas.size:
        if na_last is None:
            frame[which_nas, :] = np.nan
        elif na_last:
            frame[which_nas, :] = np.inf
        else:
            frame[which_nas, :] = -np.inf

    if which_blanks.size:
        if blank_last is None:
            frame[which_blanks, :] = np.nan
        elif blank_last:
            frame[which_blanks, :] = 1e99
        else:
            frame[which_blanks, :] = -1e99

    columns = tuple(frame[:, col] for col in range(frame.shape[1]))
    if not columns:
        columns = (np.zeros(len(items), dtype=float),)
    return _r_order(*columns, decreasing=decreasing, na_last=None)
