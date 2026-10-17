"""shift, nafill, fcoalesce, fifelse, and copy."""

from __future__ import annotations

import copy as copy_mod
import math

import numpy as np

from datatable._util import DataTableError, as_sequence, column_list, is_na, r_type, vector_type


def _fill_value(fill, kind: str):
    if fill is None or (isinstance(fill, float) and math.isnan(fill)):
        return None
    if kind == "integer":
        return int(fill)
    if kind == "double":
        return float(fill)
    if kind == "logical":
        return bool(fill)
    if kind == "character":
        return str(fill)
    return fill


def _shift_one(values, n: int, fill, kind: str, cyclic: bool):
    nrow = len(values)
    if nrow == 0:
        return []
    step = abs(n) % nrow if cyclic else min(abs(n), nrow)
    positive_lag = n >= 0
    out = [None] * nrow
    if positive_lag:
        if step < nrow:
            out[step:] = values[: nrow - step]
        if cyclic:
            out[:step] = values[nrow - step :]
        else:
            for index in range(step):
                out[index] = fill
    else:
        if step < nrow:
            out[: nrow - step] = values[step:]
        if cyclic:
            out[nrow - step :] = values[:step]
        else:
            for index in range(nrow - step, nrow):
                out[index] = fill
    if kind == "double":
        return [float("nan") if item is None else float(item) for item in out]
    return out


def shift(x, n=1, fill=None, type="lag", give_names=False):
    """Lag, lead, or cyclic shift. A matrix stops with data.table's message."""
    if isinstance(x, np.ndarray) and x.ndim > 1:
        raise DataTableError(
            "shift input must not be matrix or array, consider wrapping it into data.table() or c()"
        )
    choices = ("lag", "lead", "shift", "cyclic")
    if type not in choices:
        raise DataTableError(f"type must be one of {', '.join(choices)}")
    if isinstance(n, float) and math.isnan(n):
        raise DataTableError("Item 1 of n is NA")
    counts = as_sequence(n)
    if any(is_na(item) for item in counts):
        for index, item in enumerate(counts, start=1):
            if is_na(item):
                raise DataTableError(f"Item {index} of n is NA")
    try:
        counts = [int(item) for item in counts]
    except (TypeError, ValueError):
        raise DataTableError("is.numeric(n) is not TRUE") from None
    if type == "cyclic" and fill is not None:
        pass
    cyclic = type == "cyclic"
    if column_list(x):
        columns = [list(as_sequence(column)) for column in x]
        names = [f"V{index}" for index in range(1, len(columns) + 1)]
    else:
        columns = [list(as_sequence(x))]
        names = ["V1"]
    pieces = []
    labels = []
    for name, column in zip(names, columns):
        kind = vector_type(column)
        for count in counts:
            direction = type
            amount = count
            if type == "lead":
                amount = -count
                direction = "lead"
            elif type == "shift":
                direction = "lag"
            if give_names and type in ("lag", "lead") and amount < 0:
                direction = "lead" if direction == "lag" else "lag"
                amount = -amount
            if give_names and type == "lead" and count == 0 and any(item < 0 for item in counts) and any(item > 0 for item in counts):
                direction = "lag"
            piece_fill = _fill_value(fill, kind)
            moved = count if type != "lead" else -count
            if type == "lead":
                moved = -count
            values = _shift_one(column, moved if type != "shift" else count, piece_fill, kind, cyclic)
            if type == "lead":
                values = _shift_one(column, -count, piece_fill, kind, cyclic)
            elif type == "shift":
                values = _shift_one(column, count, piece_fill, kind, False)
            else:
                values = _shift_one(column, count, piece_fill, kind, cyclic)
            pieces.append(values)
            labels.append(f"{name}_{direction}_{abs(amount) if type in ('lag', 'lead') and amount < 0 else amount}")
    if give_names and len(pieces) != 1:
        return dict(zip(labels, pieces))
    if len(pieces) == 1:
        return pieces[0]
    return pieces


def nafill(x, type="const", fill=None, nan=None):
    """Fill missing values by a constant, last observation, or next observation."""
    choices = ("const", "locf", "nocb")
    if type not in choices:
        raise DataTableError(f"type must be one of {', '.join(choices)}")
    values = list(as_sequence(x))
    if len(values) == 0:
        return []
    nan_is_na = nan is None or (isinstance(nan, float) and math.isnan(nan) is False and nan is None)
    # R default nan=NA means NaN counts as missing. nan=NaN keeps NaN.
    treat_nan_missing = not (isinstance(nan, float) and math.isnan(nan))

    def missing(item) -> bool:
        if item is None:
            return True
        if isinstance(item, float) and math.isnan(item):
            return treat_nan_missing
        return False

    kind = vector_type([item for item in values if not missing(item)] or values)
    replacement = _fill_value(fill, kind)
    if kind == "double" and replacement is None:
        replacement = float("nan")
    out = list(values)
    if type == "const":
        return [replacement if missing(item) else item for item in values]
    if type == "locf":
        carry = replacement
        filled = []
        for item in values:
            if missing(item):
                filled.append(carry)
            else:
                carry = item
                filled.append(item)
        return filled
    carry = replacement
    filled = [None] * len(values)
    for index in range(len(values) - 1, -1, -1):
        item = values[index]
        if missing(item):
            filled[index] = carry
        else:
            carry = item
            filled[index] = item
    return filled


def fcoalesce(*args, nan=None):
    """First non-missing value at each position. Types must already match."""
    if len(args) == 0:
        return None
    if args[0] is None:
        return None
    treat_nan_missing = not (isinstance(nan, float) and math.isnan(nan))
    vectors = []
    for arg in args:
        if arg is None:
            vectors.append([None])
        elif column_list(arg):
            raise DataTableError(
                "The first argument is a list, data.table or data.frame. In this case there should be no other arguments provided."
            ) if len(args) != 1 else None
            if len(args) == 1:
                return fcoalesce(*arg, nan=nan)
        else:
            vectors.append(list(as_sequence(arg)))
    if vectors[0] == [None] and args[0] is None:
        return None
    first = vectors[0]
    if len(vectors) == 1:
        return list(first)

    def missing(item) -> bool:
        if item is None:
            return True
        if isinstance(item, float) and math.isnan(item):
            return treat_nan_missing
        return False

    def concrete(values):
        for item in values:
            if not missing(item):
                return r_type(item)
        return None

    first_type = concrete(first)
    nrow = len(first)
    for index, item in enumerate(vectors[1:], start=2):
        item_type = concrete(item)
        if first_type is not None and item_type is not None and item_type != first_type:
            raise DataTableError(
                f"Item {index} is type {item_type} but the first item is type {first_type}. Please coerce before coalescing."
            )
        if len(item) != 1 and len(item) != nrow:
            raise DataTableError(
                f"Item {index} is length {len(item)} but the first item is length {nrow}. Only singletons are recycled."
            )
    columns = []
    for item in vectors:
        if len(item) == 1 and nrow != 1:
            columns.append(item * nrow)
        else:
            columns.append(item)
    out = []
    for row in range(nrow):
        chosen = columns[0][row]
        if missing(chosen):
            for column in columns[1:]:
                if not missing(column[row]):
                    chosen = column[row]
                    break
        out.append(chosen)
    return out


def fifelse(test, yes, no, na=None):
    """Vector if/else. test must be logical, and yes, no, and na share one type."""
    tests = list(as_sequence(test))
    for item in tests:
        if item is None:
            continue
        if not isinstance(item, (bool,)):
            raise DataTableError("Argument 'test' must be logical.")
    yes_values = list(as_sequence(yes))
    no_values = list(as_sequence(no))
    na_values = list(as_sequence(na))
    n = len(tests)

    def check(values, name):
        if len(values) != 1 and len(values) != n:
            raise DataTableError(
                f"Length of '{name}' is {len(values)} but must be 1 or length of 'test' ({n})."
            )
        if len(values) == 1 and n != 1:
            return values * n
        return values

    yes_values = check(yes_values, "yes")
    no_values = check(no_values, "no")
    na_values = check(na_values, "na")

    def concrete(values):
        for item in values:
            if not is_na(item):
                return r_type(item)
        return None

    yes_type = concrete(yes_values)
    no_type = concrete(no_values)
    if yes_type is not None and no_type is not None and yes_type != no_type:
        raise DataTableError(
            f"'no' is of type {no_type} but 'yes' is {yes_type}. Please make all arguments have the same type."
        )
    out = []
    for item, yes_item, no_item, na_item in zip(tests, yes_values, no_values, na_values):
        if item is None:
            out.append(na_item)
        elif item:
            out.append(yes_item)
        else:
            out.append(no_item)
    return out


def copy(x):
    """Duplicate a vector or a plain list."""
    if column_list(x):
        return [copy(item) for item in x]
    if isinstance(x, np.ndarray):
        return x.copy()
    values = as_sequence(x)
    return copy_mod.deepcopy(values)
