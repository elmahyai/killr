"""Melt vectors, lists, arrays, and data frames the way reshape2 1.4.5 does.

The data-frame method follows ``melt_dataframe``: id columns are repeated
once per measure, the ``variable`` column is a factor, and measure columns
are concatenated at the widest R type. List melting stacks the pieces and
adds an ``L`` label. Array melting expands the dimensions in column-major
order, the same order as ``expand.grid``.
"""

from __future__ import annotations

import sys
import warnings
from typing import Any

from reshape2.convert import type_convert
from reshape2.frame import (
    Column,
    DataFrame,
    as_column,
    attributes_equal,
    coerce_value,
    factor_labels,
    is_factor,
    is_missing_value,
    is_na,
    is_posixlt,
    promote,
    repeat_each,
    repeat_vector,
    type_rank,
)


_MISSING = object()


class List(list):
    """An R list. A plain ``list`` is also an R list; this one can be named."""

    def __init__(self, components, names=None, varname=None):
        super().__init__(components)
        if names is None:
            self.names = None
        else:
            stored = [None if is_na(name) else str(name) for name in names]
            if len(stored) < len(components):
                stored.extend([None] * (len(components) - len(stored)))
            elif len(stored) > len(components):
                raise ValueError("'names' attribute must be the same length as the vector")
            self.names = stored
        self.varname = varname


class Array:
    """An array stored in column-major order, with optional dimnames."""

    def __init__(self, data, dimnames=None, names=None):
        import numpy as np

        self.data = data if isinstance(data, np.ndarray) else np.array(data, dtype=object)
        self.dimnames = dimnames
        self.names = names


def _take(kwargs: dict, *names: str, default: Any = _MISSING) -> Any:
    for name in names:
        if name in kwargs:
            return kwargs.pop(name)
    return default


def _is_frame(data: Any) -> bool:
    return isinstance(data, (DataFrame, dict))


def _is_array(data: Any) -> bool:
    if isinstance(data, Array):
        return True
    try:
        import numpy as np
    except ImportError:
        return False
    return isinstance(data, np.ndarray) and data.ndim >= 2


def _is_r_list(data: Any) -> bool:
    return isinstance(data, list) and not isinstance(data, DataFrame)


def _frame(data: Any) -> DataFrame:
    if isinstance(data, DataFrame):
        return data
    columns = []
    for name, values in data.items():
        columns.append((str(name), as_column(values)))
    return DataFrame(columns)


def _atomic(data: Any) -> Column:
    if isinstance(data, Column):
        return data.copy()
    if isinstance(data, tuple):
        return as_column(list(data))
    try:
        import numpy as np

        if isinstance(data, np.ndarray) and data.ndim <= 1:
            return as_column(data.tolist())
    except ImportError:
        pass
    if isinstance(data, list):
        raise TypeError("an R list is melted with melt.list; pass a tuple for an atomic vector")
    return as_column([data] if not _is_sequence(data) else data)


def _is_sequence(data: Any) -> bool:
    return isinstance(data, (list, tuple))


def melt(data: Any, *args: Any, **kwargs: Any) -> DataFrame:
    """Melt ``data`` into a long data frame.

    A dict or :class:`DataFrame` uses the data-frame method. A NumPy array
    of rank 2 or more, or an :class:`Array`, uses the array method. A list
    uses the list method. A tuple, a one-dimensional array, or a scalar uses
    the vector method. ``na.rm`` and ``value.name`` are keyword arguments,
    as they are in R, because they sit after ``...``.
    """

    na_rm = _take(kwargs, "na_rm", "na.rm", default=False)
    value_name = _take(kwargs, "value_name", "value.name", default="value")
    level = _take(kwargs, "level", default=1)
    if _is_frame(data):
        return melt_data_frame(data, *args, na_rm=na_rm, value_name=value_name, **kwargs)
    if _is_array(data):
        return melt_array(data, *args, na_rm=na_rm, value_name=value_name, **kwargs)
    if _is_r_list(data):
        return melt_list(data, *args, na_rm=na_rm, value_name=value_name, level=level, **kwargs)
    return melt_default(data, na_rm=na_rm, value_name=value_name)


def melt_default(data: Any, na_rm: bool = False, value_name: str = "value", **_ignored: Any) -> DataFrame:
    """Melt an atomic vector into one column."""

    column = _atomic(data)
    values = list(column.values)
    if na_rm:
        values = [value for value in values if not is_missing_value(value, column.storage)]
    return DataFrame([(str(value_name), Column(column.storage, values, column.attributes))])


def melt_list(data: Any, *args: Any, na_rm: bool = False, value_name: str = "value", level: int = 1, **kwargs: Any) -> DataFrame:
    """Melt each component and bind the rows, then add the list label."""

    parts = [melt(part, *args, na_rm=na_rm, value_name=value_name, level=level + 1, **kwargs) for part in data]
    result = _rbind_fill(parts)
    if isinstance(data, List) and data.names is not None:
        base: list[Any] = list(data.names)
        storage = "character"
    else:
        base = list(range(1, len(data) + 1))
        storage = "integer"
    lengths = [0 if part is None else part.nrows for part in parts]
    labels: list[Any] = []
    for label, size in zip(base, lengths):
        labels.extend([label] * size)
    varname = data.varname if isinstance(data, List) else None
    label_var = str(varname) if varname else f"L{level}"
    if result is None:
        result = DataFrame([], nrows=0)
    else:
        result = result.copy()
    result.columns.append((label_var, Column(storage, labels)))
    result.nrows = len(labels)
    return result


def melt_array(
    data: Any,
    *args: Any,
    na_rm: bool = False,
    value_name: str = "value",
    **kwargs: Any,
) -> DataFrame:
    """Melt an array. Dimnames are converted unless ``as.is`` is true."""

    varnames = _take(kwargs, "varnames", default=_MISSING)
    as_is = _take(kwargs, "as_is", "as.is", default=False)
    if args:
        if varnames is not _MISSING:
            raise TypeError("melt.array received varnames twice")
        varnames = args[0]
    array, labels, dim_names = _array_parts(data)
    if varnames is _MISSING:
        varnames = dim_names
    converted = []
    for column in labels:
        if not as_is and column.storage == "character":
            typed = type_convert(column.values, as_is=True)
            if typed.storage == "character":
                typed = _factor_appearance(typed)
            converted.append(typed)
        else:
            converted.append(column)
    if varnames is None:
        names = [f"Var{index + 1}" for index in range(len(converted))]
    else:
        names = [str(name) for name in varnames]
        if len(names) != len(converted):
            raise ValueError(
                f"'names' attribute [{len(names)}] must be the same length as the vector [{len(converted)}]"
            )
    grid = _expand_grid(converted)
    flat = _ravel(array)
    value = as_column(flat)
    columns = [(name, column) for name, column in zip(names, grid)]
    columns.append((str(value_name), value))
    frame = DataFrame(columns)
    if na_rm:
        keep = [
            not is_missing_value(item, value.storage)
            for item in value.values
        ]
        frame = _filter_rows(frame, keep)
    return frame


def melt_data_frame(
    data: Any,
    *args: Any,
    na_rm: bool = False,
    value_name: str = "value",
    **kwargs: Any,
) -> DataFrame:
    """Melt a data frame into id columns, a variable factor, and a value column."""

    id_vars = _take(kwargs, "id_vars", "id.vars", "id", default=_MISSING)
    measure_vars = _take(kwargs, "measure_vars", "measure.vars", "measure", default=_MISSING)
    variable_name = _take(kwargs, "variable_name", "variable.name", "variable", default="variable")
    factors_as_strings = _take(
        kwargs, "factors_as_strings", "factorsAsStrings", "factors.as.strings", default=True
    )
    if args:
        if id_vars is not _MISSING:
            raise TypeError("melt.data.frame received id.vars twice")
        id_vars = args[0]
        args = args[1:]
    if args:
        if measure_vars is not _MISSING:
            raise TypeError("melt.data.frame received measure.vars twice")
        measure_vars = args[0]
        args = args[1:]
    if args:
        variable_name = args[0]
    original_id = id_vars
    id_missing = id_vars is _MISSING
    measure_missing = measure_vars is _MISSING
    frame = _frame(data)
    id_names, measure_names = _melt_check(
        frame, id_vars, measure_vars, variable_name, value_name, id_missing, measure_missing
    )
    if len(measure_names) == 0:
        return _subset_frame(frame, original_id, id_missing)
    id_index = [_match_name(frame, name) for name in id_names]
    measure_index = [_match_name(frame, name) for name in measure_names]
    factors_as_strings, measure_attributes = _normalize(frame, measure_index, bool(factors_as_strings))
    return _melt_frame(
        frame,
        id_index,
        measure_index,
        str(variable_name),
        str(value_name),
        factors_as_strings,
        measure_attributes,
        bool(na_rm),
    )


def _match_name(frame: DataFrame, name: str) -> int:
    for index, (key, _) in enumerate(frame.columns):
        if key == name:
            return index
    raise ValueError(f"id variables not found in data: {name}")


def _melt_check(frame, id_vars, measure_vars, variable_name, value_name, id_missing, measure_missing):
    varnames = frame.names()
    if not id_missing and _is_numeric_index(id_vars):
        id_vars = _subset_names(varnames, id_vars)
    if not measure_missing and _is_numeric_index(measure_vars):
        measure_vars = _subset_names(varnames, measure_vars)
    if not id_missing:
        _require_known(id_vars, varnames, "id")
    if not measure_missing:
        _require_known(measure_vars, varnames, "measure")
    if id_missing and measure_missing:
        discrete = []
        measured = []
        for name, column in frame.columns:
            if column.storage in ("character", "logical") or is_factor(column):
                discrete.append(name)
            else:
                measured.append(name)
        id_vars = discrete
        measure_vars = measured
        if id_vars:
            print("Using " + ", ".join(id_vars) + " as id variables", file=sys.stderr)
        else:
            print("No id variables; using all as measure variables", file=sys.stderr)
    elif id_missing:
        measure_vars = _as_name_list(measure_vars)
        id_vars = [name for name in varnames if name not in set(measure_vars)]
    elif measure_missing:
        id_vars = _as_name_list(id_vars)
        measure_vars = [name for name in varnames if name not in set(id_vars)]
    else:
        id_vars = _as_name_list(id_vars)
        measure_vars = _as_name_list(measure_vars)
    if not _is_string(variable_name):
        raise ValueError("'variable.name' should be a string")
    if not _is_string(value_name):
        raise ValueError("'value.name' should be a string")
    return list(id_vars), list(measure_vars)


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _is_numeric_index(value: Any) -> bool:
    if isinstance(value, bool) or is_na(value) or isinstance(value, str):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, (list, tuple)):
        if not value:
            return False
        return all(
            (isinstance(item, (int, float)) and not isinstance(item, bool)) or is_na(item)
            for item in value
        )
    return False


def _as_name_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str) or is_na(value):
        return [value]
    return list(value)


def _subset_names(varnames: list[str], index: Any) -> list[Any]:
    if isinstance(index, (int, float)) and not isinstance(index, bool):
        index = [index]
    numbers = []
    for item in index:
        if is_na(item):
            numbers.append(None)
        else:
            numbers.append(int(item))
    if any(item is not None and item < 0 for item in numbers):
        if any(item is not None and item > 0 for item in numbers):
            raise ValueError("only 0's may be mixed with negative subscripts")
        dropped = {abs(item) for item in numbers if item not in (None, 0)}
        return [name for pos, name in enumerate(varnames, start=1) if pos not in dropped]
    out = []
    for item in numbers:
        if item is None or item == 0:
            if item is None:
                out.append(None)
            continue
        if item > len(varnames):
            out.append(None)
        else:
            out.append(varnames[item - 1])
    return out


def _require_known(names: Any, varnames: list[str], kind: str) -> None:
    selected = _as_name_list(names)
    unknown = []
    for name in selected:
        if name is None or name not in varnames:
            unknown.append("NA" if name is None else str(name))
    if unknown:
        raise ValueError(f"{kind} variables not found in data: {', '.join(unknown)}")


def _subset_frame(frame: DataFrame, index: Any, missing: bool) -> DataFrame:
    if missing:
        return frame.copy()
    if index is None:
        return DataFrame([], nrows=frame.nrows)
    if _is_numeric_index(index):
        names = _subset_names(frame.names(), index)
        picked = []
        for name in names:
            if name is None:
                raise ValueError("undefined columns selected")
            column = frame.column(name)
            picked.append((name, column.copy()))
        return DataFrame(picked, nrows=frame.nrows)
    selected = _as_name_list(index)
    if not selected:
        return DataFrame([], nrows=frame.nrows)
    picked = []
    for name in selected:
        column = frame.column(str(name))
        if column is None:
            raise ValueError(f"undefined columns selected: {name}")
        picked.append((str(name), column.copy()))
    return DataFrame(picked)


def _normalize(frame: DataFrame, measure_index: list[int], factors_as_strings: bool):
    columns = [frame.columns[index][1] for index in measure_index]
    attribute_list = [dict(column.attributes) for column in columns]
    equal = all(attributes_equal(columns[0], column) for column in columns) if columns else True
    measure_attributes = dict(attribute_list[0]) if equal and attribute_list and attribute_list[0] else None
    if not equal:
        warnings.warn(
            "attributes are not identical across measure variables; they will be dropped",
            UserWarning,
            stacklevel=3,
        )
        measure_attributes = None
    if not factors_as_strings and not equal:
        warnings.warn(
            "cannot avoid coercion of factors when measure attributes not identical",
            UserWarning,
            stacklevel=3,
        )
        factors_as_strings = True
    if factors_as_strings and any(is_factor(column) for column in columns):
        measure_attributes = None
    return factors_as_strings, measure_attributes


def _melt_frame(
    frame: DataFrame,
    id_index: list[int],
    measure_index: list[int],
    variable_name: str,
    value_name: str,
    factors_as_strings: bool,
    measure_attributes: dict | None,
    na_rm: bool,
) -> DataFrame:
    measure_columns = [frame.columns[index][1] for index in measure_index]
    for column in measure_columns:
        if column.storage not in ("logical", "integer", "double", "complex", "character", "raw") or is_posixlt(column):
            if column.storage == "list" or is_posixlt(column):
                raise ValueError("Can't melt data.frames with non-atomic 'measure' columns")
    n_measure = len(measure_index)
    out_columns: list[tuple[str, Column]] = []
    for index in id_index:
        name, column = frame.columns[index]
        if is_posixlt(column):
            raise ValueError(f"'{name}' is a POSIXlt. Please convert to POSIXct.")
        repeated = Column(
            column.storage,
            repeat_vector(column.values, n_measure),
            dict(column.attributes),
        )
        out_columns.append((name, repeated))
    measure_names = [frame.columns[index][0] for index in measure_index]
    codes = repeat_each(list(range(1, n_measure + 1)), frame.nrows)
    out_columns.append(
        (variable_name, Column("integer", codes, {"levels": list(measure_names), "class": "factor"}))
    )
    value = _concatenate(measure_columns, factors_as_strings)
    if measure_attributes:
        value.attributes = dict(measure_attributes)
    out_columns.append((value_name, value))
    result = DataFrame(out_columns)
    if na_rm:
        keep = [not is_missing_value(item, value.storage) for item in value.values]
        result = _filter_rows(result, keep)
    return result


def _value_storage(column: Column, factors_as_strings: bool) -> str:
    if is_factor(column) and factors_as_strings:
        return "character"
    return column.storage


def _concatenate(columns: list[Column], factors_as_strings: bool) -> Column:
    if not columns:
        return Column("logical", [])
    target = _value_storage(
        max(columns, key=lambda column: type_rank(column.storage, column, factors_as_strings)),
        factors_as_strings,
    )
    values: list[Any] = []
    for column in columns:
        values.extend(_coerce_column(column, target, factors_as_strings))
    return Column(target, values)


def _coerce_column(column: Column, target: str, factors_as_strings: bool) -> list[Any]:
    if is_factor(column) and factors_as_strings and target == "character":
        return factor_labels(column)
    if is_factor(column) and target == "integer":
        return list(column.values)
    if column.storage == target and not is_factor(column):
        return list(column.values)
    return [coerce_value(value, column.storage, target) for value in column.values]


def _factor_appearance(column: Column) -> Column:
    levels: list[str] = []
    for value in column.values:
        if value is not None and value not in levels:
            levels.append(value)
    index = {level: code for code, level in enumerate(levels, start=1)}
    codes = [None if value is None else index[value] for value in column.values]
    return Column("integer", codes, {"levels": levels, "class": "factor"})


def _array_parts(data: Any):
    import numpy as np

    if isinstance(data, Array):
        array = np.array(data.data, dtype=object) if data.data.dtype == object else data.data
        dimnames = data.dimnames
        names = data.names
    else:
        array = data
        dimnames = getattr(data, "dimnames", None)
        names = getattr(data, "dimname_names", None)
    shape = array.shape
    labels = []
    if dimnames is None:
        dimnames = [None] * array.ndim
    for index, size in enumerate(shape):
        stored = dimnames[index] if index < len(dimnames) else None
        if stored is None:
            labels.append(Column("integer", list(range(1, int(size) + 1))))
        else:
            labels.append(Column("character", [None if is_na(item) else str(item) for item in stored]))
    return array, labels, names


def _ravel(array: Any) -> list[Any]:
    import numpy as np

    flat = np.ravel(array, order="F")
    values = flat.tolist()
    if array.dtype.kind in "iu":
        return [int(value) for value in values]
    if array.dtype.kind == "f":
        out = []
        for value in values:
            if isinstance(value, float) and value != value:
                out.append(float("nan"))
            else:
                out.append(float(value))
        return out
    if array.dtype.kind == "b":
        return [bool(value) for value in values]
    if array.dtype.kind == "c":
        return [complex(value) for value in values]
    cleaned = []
    for value in values:
        if is_na(value):
            cleaned.append(None)
        elif isinstance(value, float) and value != value:
            cleaned.append(float("nan"))
        else:
            cleaned.append(value)
    return cleaned


def _expand_grid(columns: list[Column]) -> list[Column]:
    lengths = [len(column) for column in columns]
    total = 1
    for length in lengths:
        total *= length
    if total == 0:
        return [Column(column.storage, [], column.attributes) for column in columns]
    grid = []
    stride = 1
    for column, length in zip(columns, lengths):
        reps = total // (stride * length)
        values = repeat_vector(repeat_each(column.values, stride), reps)
        grid.append(Column(column.storage, values, column.attributes))
        stride *= length
    return grid


def _filter_rows(frame: DataFrame, keep: list[bool]) -> DataFrame:
    columns = []
    for name, column in frame.columns:
        columns.append((name, Column(column.storage, [value for value, flag in zip(column.values, keep) if flag], column.attributes)))
    return DataFrame(columns)


def _rbind_fill(frames: list[DataFrame | None]) -> DataFrame | None:
    frames = [frame for frame in frames if frame is not None]
    if not frames:
        return None
    if len(frames) == 1:
        return frames[0]
    order: list[str] = []
    seen: set[str] = set()
    for frame in frames:
        for name, _ in frame.columns:
            if name not in seen:
                seen.add(name)
                order.append(name)
    nrows = sum(frame.nrows for frame in frames)
    if not order:
        return DataFrame([], nrows=nrows)
    plans = {name: _column_plan(name, frames) for name in order}
    filled = {name: [None] * nrows for name in order}
    position = 0
    for frame in frames:
        for name, column in frame.columns:
            storage, attributes, as_factor = plans[name]
            _write_slice(filled[name], position, column, storage, attributes, as_factor)
        position += frame.nrows
    columns = []
    for name in order:
        storage, attributes, _as_factor = plans[name]
        columns.append((name, Column(storage, filled[name], attributes)))
    return DataFrame(columns, nrows=nrows)


def _column_plan(name: str, frames: list[DataFrame]):
    present = []
    for frame in frames:
        column = frame.column(name)
        if column is not None:
            present.append(column)
    first = present[0]
    if all(is_factor(column) for column in present):
        levels: list[str] = []
        for column in present:
            for level in column.attributes.get("levels", []):
                if level not in levels:
                    levels.append(level)
        return "integer", {"levels": levels, "class": "factor"}, True
    if is_factor(first) and not all(is_factor(column) for column in present):
        return "character", {}, False
    storage = first.storage
    for column in present[1:]:
        storage = promote(storage, "character" if is_factor(column) else column.storage)
    attributes = dict(first.attributes) if storage == first.storage and all(attributes_equal(column, first) for column in present) else {}
    if storage != first.storage:
        attributes = {}
    return storage, attributes, False


def _write_slice(target: list[Any], position: int, column: Column, storage: str, attributes: dict, as_factor: bool) -> None:
    if as_factor:
        levels = attributes.get("levels", [])
        index = {str(level): code for code, level in enumerate(levels, start=1)}
        source_levels = [str(level) for level in column.attributes.get("levels", [])]
        for offset, code in enumerate(column.values):
            if code is None:
                target[position + offset] = None
            else:
                target[position + offset] = index[source_levels[int(code) - 1]]
        return
    source = column
    if is_factor(column) and storage == "character":
        values = factor_labels(column)
        source_storage = "character"
    else:
        values = column.values
        source_storage = column.storage
    for offset, value in enumerate(values):
        target[position + offset] = coerce_value(value, source_storage, storage)
    del source
