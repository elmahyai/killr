"""A grid of predictor values.

Unique values are crossed with the first column changing slowest, which is
what tidyr::expand does. A model fills any predictor that was not named with
typical().
"""

from __future__ import annotations

from modelr.design import predictor_vars
from modelr.frame import Factor, Frame, as_frame, is_na
from modelr.typical import typical


def data_grid(data, *columns, model=None, **assigned):
    if not columns and not assigned and model is None:
        raise ValueError("Must supply at least one of `...` and `.model`")
    frame = as_frame(data)
    pairs = []
    for column in columns:
        if not isinstance(column, str):
            raise TypeError("pass column names as strings")
        pairs.append((column, _unique_values(frame.columns[column])))
    for name, value in assigned.items():
        pairs.append((name, _supplied_values(value)))
    expanded = _cross(pairs) if pairs else None
    if model is None:
        return expanded
    have = [] if expanded is None else expanded.names()
    needed = [name for name in predictor_vars(model) if name not in have]
    if needed:
        typical_pairs = []
        for name in needed:
            typical_pairs.append((name, _box(typical(frame.columns[name]))))
        typical_frame = _cross(typical_pairs)
    else:
        typical_frame = None
    return _cross_frames(expanded, typical_frame)


def _box(value):
    if isinstance(value, list):
        return value
    return [value]


def _unique_values(column):
    if isinstance(column, Factor):
        seen = {value for value in column.values if value is not None}
        return [level for level in column.levels if level in seen]
    if column and all(value is None or isinstance(value, str) for value in column):
        return sorted({value for value in column if value is not None})
    numbers = [float(value) for value in column if not is_na(value)]
    return sorted(set(numbers))


def _supplied_values(value):
    if isinstance(value, Factor):
        return _unique_values(value)
    values = list(value)
    if not values:
        return []
    if all(item is None or isinstance(item, str) for item in values):
        return sorted({item for item in values if item is not None})
    return sorted({float(item) for item in values if not is_na(item)})


def _cross(pairs):
    names = [name for name, _values in pairs]
    rows = [[]]
    for _name, values in pairs:
        rows = [row + [value] for row in rows for value in values]
    columns = {name: [] for name in names}
    for row in rows:
        for name, value in zip(names, row):
            columns[name].append(value)
    return Frame(columns)


def _cross_frames(left, right):
    if left is None:
        return right
    if right is None:
        return left
    columns = {}
    for name in left.names():
        column = []
        for i in range(left.nrow):
            column.extend([_at(left.columns[name], i)] * right.nrow)
        columns[name] = column
    for name in right.names():
        column = []
        for _ in range(left.nrow):
            column.extend(_as_list(right.columns[name]))
        columns[name] = column
    return Frame(columns)


def _at(column, index):
    if isinstance(column, Factor):
        return column.values[index]
    return column[index]


def _as_list(column):
    if isinstance(column, Factor):
        return list(column.values)
    return list(column)
