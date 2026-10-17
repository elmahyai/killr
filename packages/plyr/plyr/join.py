"""Join two data frames the way plyr 1.8.9 ``join`` does.

The row order of ``x`` is kept. Rows from ``y`` are added at the bottom only
for a full join. Matching keys are the rows of ``rbind.fill`` on the ``by``
columns, so a number matches its double and a factor matches its label.
``match = "all"`` repeats every matching row. ``match = "first"`` keeps the
earliest one. Rcpp's ``split_indices`` is not used.
"""

from __future__ import annotations

import math
import sys

import numpy as np

from plyr.rbind_fill import DataFrame, Factor, Matrix, Posixct, rbind_fill


_TYPE_CHOICES = ("left", "right", "inner", "full")
_MATCH_CHOICES = ("first", "all")


def _match_arg(value, choices):
    """``match.arg``: ``None`` is the first choice, and a unique prefix matches."""
    if value is None:
        return choices[0]
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError("'arg' must be of length 1")
        value = value[0]
    if not isinstance(value, str):
        raise ValueError("'arg' must be of length 1")
    if value in choices:
        return value
    partial = [choice for choice in choices if choice.startswith(value)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise ValueError(f"'arg' should be one of {quoted}")


def _as_by(by):
    if isinstance(by, str):
        return [by]
    return ["" if name is None else str(name) for name in by]


def _as_frame(obj):
    if isinstance(obj, DataFrame):
        return obj
    if isinstance(obj, dict):
        return DataFrame(obj)
    columns = getattr(obj, "columns", None)
    if isinstance(columns, dict):
        return DataFrame(columns, row_names=getattr(obj, "row_names", None))
    raise ValueError("join requires data frames")


def _scalar(value):
    if isinstance(value, np.generic):
        if isinstance(value, np.floating):
            number = float(value)
            if math.isnan(number):
                return float("nan")
            return number
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.integer):
            return int(value)
        return value.item()
    return value


def _value_at(column, index):
    if isinstance(column, Factor):
        code = column.codes[index]
        return None if code is None else int(code)
    if isinstance(column, Posixct):
        return column.seconds[index]
    if isinstance(column, Matrix):
        return tuple(_scalar(item) for item in np.asarray(column.data[index]).ravel())
    if isinstance(column, np.ndarray):
        if column.ndim <= 1:
            return _scalar(column[index])
        return tuple(_scalar(item) for item in np.asarray(column[index]).ravel())
    return column[index]


def _token(value):
    """Equality key. ``NA`` matches ``NA``, ``NaN`` matches ``NaN``, and ``-0`` matches ``0``."""
    if isinstance(value, tuple):
        return ("row", tuple(_token(item) for item in value))
    if value is None:
        return ("na",)
    if isinstance(value, bool):
        return ("b", bool(value))
    if isinstance(value, float):
        if math.isnan(value):
            return ("nan",)
        if value == 0.0:
            return ("z",)
        return ("d", value)
    if isinstance(value, int):
        return ("i", int(value))
    if isinstance(value, str):
        return ("c", value)
    return ("o", repr(value))


def _row_key(columns, index):
    return tuple(_token(_value_at(column, index)) for column in columns)


def _join_keys(x, y, by):
    """Ids of the bound key columns. An empty ``by`` gives every row its own id."""
    if not by:
        width = len(x)
        return [("u", index) for index in range(width)], [
            ("u", width + index) for index in range(len(y))
        ]
    x_by = DataFrame({name: x.columns[name] for name in by})
    y_by = DataFrame({name: y.columns[name] for name in by})
    joint = rbind_fill(x_by, y_by)
    bound = [joint.columns[name] for name in by]
    width = len(x)
    x_keys = [_row_key(bound, index) for index in range(width)]
    y_keys = [_row_key(bound, width + index) for index in range(len(y))]
    return x_keys, y_keys


def _expand(left_keys, right_keys, keep_unmatched):
    """Row pairs in left order. Each right group stays in the order it was seen."""
    groups = {}
    for index, key in enumerate(right_keys):
        bucket = groups.get(key)
        if bucket is None:
            groups[key] = [index]
        else:
            bucket.append(index)
    left_index = []
    right_index = []
    for index, key in enumerate(left_keys):
        hits = groups.get(key)
        if not hits:
            if keep_unmatched:
                left_index.append(index)
                right_index.append(None)
            continue
        for hit in hits:
            left_index.append(index)
            right_index.append(hit)
    return left_index, right_index


def _first_index(keys):
    found = {}
    for index, key in enumerate(keys):
        if key not in found:
            found[key] = index
    return found


def _take(column, indices):
    if isinstance(column, Factor):
        codes = []
        for index in indices:
            if index is None:
                codes.append(None)
            else:
                code = column.codes[index]
                codes.append(None if code is None else int(code))
        return Factor(
            codes,
            list(column.levels),
            ordered=column.ordered,
            attributes=dict(column.attributes),
        )
    if isinstance(column, Posixct):
        seconds = [None if index is None else column.seconds[index] for index in indices]
        return Posixct(seconds, tzone=column.tzone, attributes=dict(column.attributes))
    if isinstance(column, Matrix):
        width = len(indices)
        if width == 0:
            shape = (0, *column.data.shape[1:])
            data = np.empty(shape, dtype=object)
        else:
            rows = []
            for index in indices:
                if index is None:
                    rows.append(np.full(column.data.shape[1:], None, dtype=object))
                else:
                    rows.append(np.array(column.data[index], dtype=object, copy=True))
            data = np.stack(rows, axis=0)
        dimnames = None
        if column.dimnames is not None:
            dimnames = [None if item is None else list(item) for item in column.dimnames]
            dimnames[0] = None
        names = None if column.dimnames_names is None else list(column.dimnames_names)
        return Matrix(data, dimnames=dimnames, dimnames_names=names, attributes=dict(column.attributes))
    if isinstance(column, np.ndarray) and column.ndim > 1:
        rows = []
        for index in indices:
            if index is None:
                rows.append(tuple(None for _ in range(column.shape[1])))
            else:
                rows.append(tuple(_scalar(item) for item in np.asarray(column[index]).ravel()))
        return rows
    if isinstance(column, np.ndarray):
        return [None if index is None else _scalar(column[index]) for index in indices]
    return [None if index is None else column[index] for index in indices]


def _select(frame, names, indices):
    return {name: _take(frame.columns[name], indices) for name in names}


def _other_names(frame, by):
    skip = set(by)
    return [name for name in frame.columns if name not in skip]


def _make_unique(names):
    """R ``make.unique`` with a dot separator."""
    reserved = set(names)
    seen = {}
    unique = []
    for name in names:
        times = seen.get(name, 0)
        if times == 0:
            unique.append(name)
            seen[name] = 1
            continue
        index = times
        while f"{name}.{index}" in reserved:
            index += 1
        candidate = f"{name}.{index}"
        reserved.add(candidate)
        unique.append(candidate)
        seen[name] = index + 1
    return unique


def _row_labels(frame, indices):
    if frame.row_names is None:
        labels = [str(index + 1) for index in indices]
    else:
        labels = [frame.row_names[index] for index in indices]
    return _make_unique(labels)


def _blank_like(column, width):
    if isinstance(column, Factor):
        return Factor([None] * width, list(column.levels), ordered=column.ordered, attributes=dict(column.attributes))
    if isinstance(column, Posixct):
        return Posixct([None] * width, tzone=column.tzone, attributes=dict(column.attributes))
    if isinstance(column, Matrix):
        shape = (width, *column.data.shape[1:])
        data = np.empty(shape, dtype=object)
        data.fill(None)
        return Matrix(data, attributes=dict(column.attributes))
    return [None] * width


def _all_missing(column):
    if isinstance(column, (Factor, Posixct, Matrix, np.ndarray)):
        return False
    return all(value is None for value in column)


def _frame(columns, nrows, row_names=None):
    if not columns:
        return DataFrame({}, nrows=nrows, row_names=row_names)
    return DataFrame(columns, nrows=nrows, row_names=row_names)


def _assemble_xy(x, y, by, x_index, y_index, x_names, row_names):
    columns = {}
    columns.update(_select(x, x_names, x_index))
    columns.update(_select(y, _other_names(y, by), y_index))
    return _frame(columns, len(x_index), row_names)


def _assemble_right(x, y, by, x_index, y_index, row_names):
    columns = {}
    columns.update(_select(y, by, y_index))
    columns.update(_select(x, _other_names(x, by), x_index))
    columns.update(_select(y, _other_names(y, by), y_index))
    return _frame(columns, len(y_index), row_names)


def _level_key(level):
    if level is None:
        return ("na",)
    return ("v", level)


def _contains_double(column):
    if isinstance(column, (Factor, Posixct, Matrix)):
        return False
    values = column.tolist() if isinstance(column, np.ndarray) and column.ndim <= 1 else column
    if isinstance(column, np.ndarray) and column.ndim <= 1 and np.issubdtype(column.dtype, np.floating):
        return True
    if isinstance(column, np.ndarray) and column.ndim <= 1 and np.issubdtype(column.dtype, np.integer):
        return False
    if isinstance(values, np.ndarray):
        values = values.ravel().tolist()
    for value in values:
        value = _scalar(value)
        if isinstance(value, bool) or value is None or isinstance(value, str):
            continue
        if isinstance(value, float):
            return True
    return False


def _contains_character(column):
    if isinstance(column, (Factor, Posixct, Matrix)):
        return False
    values = column
    if isinstance(column, np.ndarray):
        values = column.ravel().tolist()
    return any(isinstance(_scalar(value), str) for value in values)


def _as_float_column(column):
    if isinstance(column, Posixct):
        return [None if value is None else float(value) for value in column.seconds]
    converted = []
    for value in column:
        if value is None:
            converted.append(None)
        elif isinstance(value, bool):
            converted.append(float(int(value)))
        else:
            converted.append(float(value))
    return converted


def _factor_labels(column):
    labels = []
    for code in column.codes:
        if code is None:
            labels.append(None)
        else:
            labels.append(column.levels[code - 1])
    return labels


def _union_levels(column, extra):
    levels = list(column.levels)
    known = {_level_key(level) for level in levels}
    for level in extra.levels:
        key = _level_key(level)
        if key not in known:
            known.add(key)
            levels.append(level)
    if len(levels) == len(column.levels):
        return column
    return Factor(list(column.codes), levels, ordered=column.ordered, attributes=dict(column.attributes))


def _promote_matched(matched, y):
    """A full join still type-promotes when every ``y`` row was already matched."""
    width = len(matched)
    for name, column in y.columns.items():
        if name not in matched.columns:
            matched.columns[name] = _blank_like(column, width)
            continue
        current = matched.columns[name]
        if isinstance(current, Factor) and isinstance(column, Factor):
            matched.columns[name] = _union_levels(current, column)
            continue
        if isinstance(current, Factor) and _contains_character(column):
            matched.columns[name] = _factor_labels(current)
            continue
        if _contains_double(column) and not isinstance(current, (Factor, Posixct, Matrix, str)):
            if not _contains_double(current) and not _contains_character(current):
                matched.columns[name] = _as_float_column(current)
    return matched


def _ordered(frame, names):
    columns = {name: frame.columns[name] for name in names}
    return DataFrame(columns, nrows=len(frame), row_names=frame.row_names)


def _full(matched, y, unmatched_index, x_names, y_only):
    if not unmatched_index:
        return _promote_matched(matched, y)
    for name in y_only:
        column = matched.columns.get(name)
        if column is not None and _all_missing(column):
            del matched.columns[name]
    for name in x_names:
        column = matched.columns.get(name)
        if column is not None and _all_missing(column) and name in y.columns:
            del matched.columns[name]
    unmatched = DataFrame(_select(y, list(y.columns), unmatched_index))
    bound = rbind_fill(matched, unmatched)
    return _ordered(bound, list(x_names) + list(y_only))


def _recycle(x_index, y_index):
    """``cbind`` recycles the shorter side when its length divides the longer one."""
    x_width = len(x_index)
    y_width = len(y_index)
    if x_width == y_width:
        return x_index, y_index, False
    if x_width == 0 or y_width == 0 or max(x_width, y_width) % min(x_width, y_width) != 0:
        raise ValueError(f"arguments imply differing number of rows: {x_width}, {y_width}")
    if x_width < y_width:
        return x_index * (y_width // x_width), y_index, True
    return x_index, y_index * (x_width // y_width), False


def _join_first(x, y, by, how):
    x_keys, y_keys = _join_keys(x, y, by)
    x_only = _other_names(x, by)
    y_only = _other_names(y, by)
    if how == "inner":
        x_at = _first_index(x_keys)
        y_at = _first_index(y_keys)
        x_index = [x_at[key] for key in y_keys if key in x_at]
        y_index = [y_at[key] for key in x_keys if key in y_at]
        x_index, y_index, discard_names = _recycle(x_index, y_index)
        row_names = None if discard_names or not x_index else _row_labels(x, x_index)
        columns = {}
        columns.update(_select(x, by, x_index))
        columns.update(_select(x, x_only, x_index))
        columns.update(_select(y, y_only, y_index))
        return _frame(columns, len(x_index), row_names)
    if how == "left":
        y_at = _first_index(y_keys)
        y_index = [y_at.get(key) for key in x_keys]
        x_index = list(range(len(x)))
        return _assemble_xy(x, y, by, x_index, y_index, list(by) + x_only, x.row_names)
    if how == "right":
        seen = set()
        for key in y_keys:
            if key in seen:
                raise ValueError("Duplicated key in y")
            seen.add(key)
        x_at = _first_index(x_keys)
        y_index = list(range(len(y)))
        x_index = [x_at.get(key) for key in y_keys]
        return _assemble_right(x, y, by, x_index, y_index, y.row_names)
    y_at = _first_index(y_keys)
    y_index = [y_at.get(key) for key in x_keys]
    x_index = list(range(len(x)))
    matched = _assemble_xy(x, y, by, x_index, y_index, list(by) + x_only, None)
    known = set(x_keys)
    unmatched_index = [index for index, key in enumerate(y_keys) if key not in known]
    return _full(matched, y, unmatched_index, list(by) + x_only, y_only)


def _join_all(x, y, by, how):
    x_keys, y_keys = _join_keys(x, y, by)
    x_names = list(x.columns)
    y_only = _other_names(y, by)
    if how == "right":
        y_index, x_index = _expand(y_keys, x_keys, True)
        return _assemble_right(x, y, by, x_index, y_index, None)
    keep = how != "inner"
    x_index, y_index = _expand(x_keys, y_keys, keep)
    if how == "full":
        matched = _assemble_xy(x, y, by, x_index, y_index, x_names, None)
        seen = {index for index in y_index if index is not None}
        unmatched_index = [index for index in range(len(y)) if index not in seen]
        return _full(matched, y, unmatched_index, x_names, y_only)
    return _assemble_xy(x, y, by, x_index, y_index, x_names, None)


def join(x, y, by=None, type="left", match="all"):
    """Join ``x`` and ``y`` by key.

    ``type`` is ``left`` (the default), ``right``, ``inner``, or ``full``.
    ``match`` is ``all`` (the default) or ``first``. A unique prefix is enough.
    ``by`` omitted uses the column names the two frames share, in ``x``'s order,
    and reports that choice on stderr.
    """
    how = _match_arg(type, _TYPE_CHOICES)
    which = _match_arg(match, _MATCH_CHOICES)
    left = _as_frame(x)
    right = _as_frame(y)
    if by is None:
        keys = [name for name in left.columns if name in right.columns]
        sys.stderr.write("Joining by: " + ", ".join(keys) + "\n")
    else:
        keys = _as_by(by)
        for name in keys:
            if name not in left.columns or name not in right.columns:
                raise ValueError("undefined columns selected")
    if which == "first":
        return _join_first(left, right, keys, how)
    return _join_all(left, right, keys, how)
