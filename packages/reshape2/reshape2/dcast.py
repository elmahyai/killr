"""Cast a molten data frame the way reshape2 1.4.5 ``dcast`` does.

The formula is split on ``~``, then on ``+`` and ``*``. ``.`` is an empty
dimension and ``...`` is every remaining column except the value column.
Cells are numbered with plyr's ``id``: the last variable in a dimension
varies fastest, and across the two output dimensions the row dimension
varies fastest. Duplicate cells are reduced with ``fun.aggregate``. When
that function is omitted and a cell occurs more than once, the reduction
is ``length`` and a message is written. Rcpp's ``split_indices`` is not
used; each group keeps the rows in input order. An empty group uses
``fill`` when it is supplied, otherwise the aggregator applied to no
values. ``mean`` and ``sum`` accumulate in long double. ``plyr::count``
is ``plyr.count.count`` and is not this reduction.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from reshape2.frame import Column, DataFrame, is_factor


_NULL = object()
_MISSING = object()
_INT_MAX = 2147483647
_INT_MIN = -2147483647
_ID_LIMIT = 2**31

_COLLATOR = None
_SORT_KEY = None


def _character_tools():
    """ICU collator used by R's ``sort`` for character vectors."""

    global _COLLATOR, _SORT_KEY
    if _COLLATOR is None:
        packages = Path(__file__).resolve().parents[2]
        plyr_path = str(packages / "plyr")
        if plyr_path not in sys.path:
            sys.path.insert(0, plyr_path)
        from plyr.count import _SortKey, _collator

        _COLLATOR = _collator()
        _SORT_KEY = _SortKey
    return _COLLATOR, _SORT_KEY


def _as_frame(data: Any) -> DataFrame:
    if isinstance(data, DataFrame):
        return data
    if isinstance(data, dict):
        return DataFrame(data)
    raise TypeError("dcast data must be a data frame")


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _missing_value(value: Any, storage: str) -> bool:
    if value is None:
        return True
    if storage == "double" and _is_nan(value):
        return True
    return False


def _key(value: Any, storage: str) -> tuple:
    if storage == "character":
        if value is None:
            return ("na",)
        return ("c", value)
    if storage == "logical":
        if value is None:
            return ("na",)
        return ("b", bool(value))
    if value is None:
        return ("na",)
    if _is_nan(value):
        return ("nan",)
    number = float(value)
    if number == 0.0:
        number = 0.0
    if storage == "integer":
        return ("i", int(number))
    return ("n", number)


def _unique(values: list[Any], storage: str) -> list[Any]:
    seen: list[Any] = []
    known: set[tuple] = set()
    for value in values:
        key = _key(value, storage)
        if key in known:
            continue
        known.add(key)
        seen.append(value)
    return seen


def _sort_present(values: list[Any], storage: str) -> list[Any]:
    if storage == "character":
        collator, sort_key = _character_tools()
        return sorted(values, key=lambda text: sort_key(collator, text))
    if storage == "logical":
        return sorted(values, key=lambda value: bool(value))
    return sorted(values, key=lambda value: float(value))


def _sorted_unique(values: list[Any], storage: str, na_last: bool) -> list[Any]:
    seen = _unique(values, storage)
    present = [value for value in seen if not _missing_value(value, storage)]
    missing = [value for value in seen if _missing_value(value, storage)]
    ordered = _sort_present(present, storage)
    if na_last:
        return ordered + missing
    return ordered


def _as_character(value: Any, storage: str) -> str:
    if value is None:
        return "NA"
    if storage == "logical" or isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if storage == "integer" or (isinstance(value, int) and not isinstance(value, bool)):
        return str(int(value))
    if isinstance(value, float) or storage == "double":
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        number = float(value)
        if number == 0.0:
            return "0"
        if abs(number) < 2**53 and number.is_integer():
            return str(int(number))
        text = format(number, ".15g")
        if "e" in text:
            mantissa, exponent = text.split("e")
            return f"{mantissa}e{int(exponent):+03d}"
        return text
    return str(value)


def _factor_label(column: Column, code: Any) -> Any:
    if code is None:
        return None
    level = column.attributes.get("levels", [])[int(code) - 1]
    if level is None:
        return None
    return str(level)


def _id_factor(column: Column, drop: bool) -> tuple[list[int], int]:
    levels = list(column.attributes.get("levels", []))
    codes = list(column.values)
    if not drop:
        if any(code is None for code in codes) and not any(level is None for level in levels):
            levels = levels + [None]
            na_code = len(levels)
            codes = [na_code if code is None else int(code) for code in codes]
        else:
            codes = [None if code is None else int(code) for code in codes]
        return codes, len(levels)
    present = sorted({int(code) for code in codes if code is not None})
    has_na = any(code is None for code in codes)
    mapping = {code: index for index, code in enumerate(present, start=1)}
    na_id = len(present) + 1
    ids = [na_id if code is None else mapping[int(code)] for code in codes]
    return ids, len(present) + (1 if has_na else 0)


def _id_atomic(column: Column) -> tuple[list[int], int]:
    if len(column) == 0:
        return [], 0
    levels = _sorted_unique(list(column.values), column.storage, na_last=True)
    mapping = {_key(level, column.storage): index for index, level in enumerate(levels, start=1)}
    ids = [mapping[_key(value, column.storage)] for value in column.values]
    return ids, len(levels)


def _id_var(column: Column, drop: bool) -> tuple[list[int], int]:
    if len(column) == 0:
        return [], 0
    if is_factor(column):
        return _id_factor(column, drop)
    return _id_atomic(column)


def _remap(ids: list[int]) -> tuple[list[int], int]:
    levels = sorted(set(ids))
    mapping = {value: index for index, value in enumerate(levels, start=1)}
    return [mapping[value] for value in ids], len(levels)


def _identify(columns: list[Column], drop: bool) -> tuple[list[int], int]:
    kept = [column for column in columns if len(column) != 0]
    if not kept:
        return [], 0
    if len(kept) == 1:
        return _id_var(kept[0], drop)
    parts = [_id_var(column, drop) for column in reversed(kept)]
    counts = [count for _ids, count in parts]
    total = 1
    for count in counts:
        total *= count
    width = len(parts[0][0])
    if total > _ID_LIMIT:
        keys = []
        for row in range(width):
            keys.append("\r".join(str(ids[row]) for ids, _count in parts))
        first: dict[str, int] = {}
        combined = []
        for key in keys:
            if key not in first:
                first[key] = len(first) + 1
            combined.append(first[key])
        if drop:
            return _remap(combined)
        return combined, total
    steps = [1]
    for count in counts[:-1]:
        steps.append(steps[-1] * count)
    combined = []
    for row in range(width):
        value = 1
        for (ids, _count), step in zip(parts, steps):
            value += (ids[row] - 1) * step
        combined.append(int(value))
    if drop:
        return _remap(combined)
    return combined, int(total)


def _combine_dimensions(parts: list[tuple[list[int], int]]) -> tuple[list[int], int]:
    """Number cells so the first dimension varies fastest.

    ``id(rev(ids), drop = FALSE)`` reverses the dimensions and then
    reverses them again inside ``id``, so the row dimension keeps step 1.
    """

    if len(parts) == 1:
        return parts[0]
    counts = [count for _ids, count in parts]
    total = 1
    for count in counts:
        total *= count
    steps = [1]
    for count in counts[:-1]:
        steps.append(steps[-1] * count)
    width = len(parts[0][0])
    combined = []
    for row in range(width):
        value = 1
        for (ids, _count), step in zip(parts, steps):
            value += (ids[row] - 1) * step
        combined.append(int(value))
    return combined, int(total)


def _ulevels(column: Column) -> Column:
    if is_factor(column):
        levels = list(column.attributes.get("levels", []))
        if any(code is None for code in column.values) and not any(level is None for level in levels):
            levels = levels + [None]
        codes = list(range(1, len(levels) + 1))
        return Column("integer", codes, {"levels": levels, "class": "factor"})
    values = _sorted_unique(list(column.values), column.storage, na_last=False)
    return Column(column.storage, values, {})


def _expand(level_columns: list[Column]) -> list[Column]:
    if not level_columns:
        return []
    widths = [len(column) for column in level_columns]
    total = 1
    for width in widths:
        total *= width
    expanded = []
    for index, column in enumerate(level_columns):
        inner = 1
        for width in widths[index + 1 :]:
            inner *= width
        outer = total // (inner * len(column)) if len(column) else 0
        values: list[Any] = []
        for _ in range(outer):
            for value in column.values:
                values.extend([value] * inner)
        expanded.append(Column(column.storage, values, dict(column.attributes)))
    return expanded


def _take(column: Column, indices: list[int]) -> Column:
    return Column(column.storage, [column.values[index] for index in indices], dict(column.attributes))


def _split_labels(columns: list[Column], ids: list[int], drop: bool) -> list[Column]:
    if not columns:
        return []
    if drop:
        first: dict[int, int] = {}
        for index, group in enumerate(ids):
            if group not in first:
                first[group] = index
        representatives = [first[group] for group in sorted(first)]
        return [_take(column, representatives) for column in columns]
    return _expand([_ulevels(column) for column in columns])


def _parse_formula(formula: Any, varnames: list[str], value_var: str) -> list[list[str]]:
    if isinstance(formula, str):
        dims = []
        for piece in formula.split("~"):
            parts = []
            for token in piece.replace("*", "+").split("+"):
                token = token.strip()
                if token != ".":
                    parts.append(token)
            dims.append(parts)
        flat = [token for dim in dims for token in dim]
        if "..." in flat:
            banned = set(flat)
            banned.add(value_var)
            remainder: list[str] = []
            for name in varnames:
                if name not in banned and name not in remainder:
                    remainder.append(name)
            expanded = []
            for dim in dims:
                if "..." in dim:
                    expanded.append([token for token in dim if token != "..."] + remainder)
                else:
                    expanded.append(dim)
            dims = expanded
        return dims
    if isinstance(formula, (list, tuple)):
        dims = []
        for dim in formula:
            if isinstance(dim, str):
                dims.append([dim])
            else:
                dims.append([str(token) for token in dim])
        return dims
    raise ValueError(f"Don't know how to parse{formula}")


def _lookup(frame: DataFrame, name: str) -> Column:
    for key, column in frame.columns:
        if key == name:
            return column
    raise ValueError(f"object '{name}' not found")


def _guess_value(frame: DataFrame) -> str:
    names = frame.names()
    if "value" in names:
        return "value"
    if "(all)" in names:
        return "(all)"
    if not names:
        raise ValueError("value.var () not found in input")
    last = names[-1]
    sys.stderr.write(f"Using {last} as value column: use value.var to override.\n")
    return last


def _upto(name: str, group: list[str]) -> list[str]:
    try:
        index = group.index(name) + 1
    except ValueError:
        return []
    return group[:index]


def _downto(name: str, group: list[str]) -> list[str]:
    return list(reversed(_upto(name, list(reversed(group)))))


def _margin_combos(var_groups: list[list[str]], margins: Any) -> list[list[str]]:
    if margins is None or margins is False:
        return []
    if margins is True:
        margins = [name for group in var_groups for name in group]
    elif isinstance(margins, str):
        margins = [margins]
    else:
        margins = [str(name) for name in margins]
    chosen = []
    for group in var_groups:
        chosen.append([name for name in group if name in set(margins)])
    nested = []
    for group, margin in zip(var_groups, chosen):
        nested.append([_downto(name, group) for name in margin])
    sequences = [[0] + list(range(1, len(dim) + 1)) for dim in nested]

    def expand(index: int) -> list[list[int]]:
        if index == len(sequences):
            return [[]]
        rows = []
        for tail in expand(index + 1):
            for head in sequences[index]:
                rows.append([head] + tail)
        return rows

    combos = []
    for index_row in expand(0):
        names: list[str] = []
        for dim, index in zip(nested, index_row):
            if index == 0:
                continue
            names.extend(dim[index - 1])
        combos.append(names)
    return combos


def _as_factor(column: Column) -> Column:
    if is_factor(column):
        return column.copy()
    levels = [_as_character(value, column.storage) for value in _sorted_unique(list(column.values), column.storage, False)]
    mapping = {level: index for index, level in enumerate(levels, start=1)}
    codes = []
    for value in column.values:
        if _missing_value(value, column.storage):
            codes.append(None)
        else:
            codes.append(mapping[_as_character(value, column.storage)])
    return Column("integer", codes, {"levels": levels, "class": "factor"})


def _add_all(column: Column) -> Column:
    factor = _as_factor(column)
    levels = list(factor.attributes.get("levels", []))
    codes = [None if code is None else int(code) for code in factor.values]
    if any(code is None for code in codes) and not any(level is None for level in levels):
        levels.append(None)
        na_code = len(levels)
        codes = [na_code if code is None else code for code in codes]
    if "(all)" not in levels:
        levels.append("(all)")
    return Column("integer", codes, {"levels": levels, "class": "factor"})


def _with_all(frame: DataFrame, names: list[str]) -> DataFrame:
    if not names:
        return frame
    columns = []
    for name, column in frame.columns:
        if name in names:
            levels = column.attributes.get("levels", [])
            code = levels.index("(all)") + 1
            columns.append((name, Column("integer", [code] * frame.nrows, dict(column.attributes))))
        else:
            columns.append((name, column.copy()))
    return DataFrame(columns, nrows=frame.nrows)


def _stack(blocks: list[DataFrame]) -> DataFrame:
    if len(blocks) == 1:
        return blocks[0]
    columns = []
    for index, (name, column) in enumerate(blocks[0].columns):
        values: list[Any] = []
        for block in blocks:
            values.extend(block.columns[index][1].values)
        columns.append((name, Column(column.storage, values, dict(column.attributes))))
    return DataFrame(columns)


def _add_margins(frame: DataFrame, var_groups: list[list[str]], margins: Any) -> DataFrame:
    combos = _margin_combos(var_groups, margins)
    if not combos:
        return frame
    converted: list[str] = []
    for combo in combos:
        for name in combo:
            if name not in converted:
                converted.append(name)
    columns = []
    for name, column in frame.columns:
        if name in converted:
            columns.append((name, _add_all(column)))
        else:
            columns.append((name, column.copy()))
    base = DataFrame(columns)
    return _stack([_with_all(base, combo) for combo in combos])


def _filter(frame: DataFrame, mask: list[Any]) -> DataFrame:
    indices = [index for index, flag in enumerate(mask) if flag is True]
    columns = [(name, _take(column, indices)) for name, column in frame.columns]
    return DataFrame(columns, nrows=len(indices))


def _storage_of(value: Any) -> str:
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "character"
    if value is None:
        return "logical"
    return "double"


def _coerce(value: Any, storage: str) -> Any:
    if storage == "double":
        if value is None:
            return None
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, float) and math.isnan(value):
            return float("nan")
        return float(value)
    if storage == "integer":
        if value is None:
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return int(value)
        return int(value)
    if storage == "logical":
        if value is None:
            return None
        return bool(value)
    if storage == "character":
        if value is None:
            return None
        return str(value)
    return value


def length(values: Any, **_kwargs: Any) -> int:
    """R's ``length`` of one aggregated cell."""

    return len(values)


def mean(values: Any, trim: float = 0, na_rm: bool = False, **kwargs: Any) -> Any:
    """R's ``mean``, accumulated in long double.

    A true missing value makes the result missing. A ``NaN`` does so only
    when no true missing value is present. ``na.rm`` drops both.
    """

    if "na.rm" in kwargs:
        na_rm = bool(kwargs.pop("na.rm"))
    if trim not in (0, 0.0):
        raise NotImplementedError("mean(trim=) is not implemented")
    total = np.longdouble(0)
    count = 0
    saw_na = False
    saw_nan = False
    for value in values:
        if value is None:
            if na_rm:
                continue
            saw_na = True
            continue
        if isinstance(value, float) and math.isnan(value):
            if na_rm:
                continue
            saw_nan = True
            continue
        if isinstance(value, bool):
            total += np.longdouble(int(value))
        else:
            total += np.longdouble(value)
        count += 1
    if saw_na:
        return None
    if saw_nan:
        return float("nan")
    if count == 0:
        return float("nan")
    return float(total / np.longdouble(count))


def sum(values: Any, na_rm: bool = False, **kwargs: Any) -> Any:
    """R's ``sum``. The first missing value decides ``NA`` or ``NaN``."""

    if "na.rm" in kwargs:
        na_rm = bool(kwargs.pop("na.rm"))
    total = np.longdouble(0)
    integer_mode = True
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            if na_rm:
                continue
            if value is None:
                return None
            return float("nan")
        if isinstance(value, bool):
            total += np.longdouble(int(value))
            continue
        if isinstance(value, float):
            integer_mode = False
            total += np.longdouble(value)
            continue
        total += np.longdouble(int(value))
    if integer_mode:
        whole = int(total)
        if _INT_MIN <= whole <= _INT_MAX and np.longdouble(whole) == total:
            return whole
        return float(total)
    return float(total)


def _resolve_fun(fun: Any) -> Any:
    if fun is None:
        return None
    if isinstance(fun, str):
        table = {"mean": mean, "sum": sum, "length": length}
        if fun not in table:
            raise ValueError(f'could not find function "{fun}"')
        return table[fun]
    return fun


def _invoke(fun: Any, values: list[Any], args: tuple, kwargs: dict) -> Any:
    if args or kwargs:
        return fun(values, *args, **kwargs)
    return fun(values)


def _cell_values(column: Column) -> tuple[list[Any], str]:
    if is_factor(column):
        return [_factor_label(column, code) for code in column.values], "character"
    return list(column.values), column.storage


def _paste_row(columns: list[Column], row: int) -> str:
    parts = []
    for column in columns:
        if is_factor(column):
            parts.append(_as_character(_factor_label(column, column.values[row]), "character"))
        else:
            parts.append(_as_character(column.values[row], column.storage))
    return "_".join(parts)


def _aggregate(
    values: list[Any],
    groups: list[int],
    total: int,
    fun: Any,
    args: tuple,
    kwargs: dict,
    fill: Any,
    source_storage: str,
) -> tuple[list[Any], str]:
    buckets: list[list[int]] = [[] for _ in range(total)]
    for index, group in enumerate(groups):
        buckets[group - 1].append(index)
    if fill is _NULL:
        if fun is mean:
            template = float("nan")
            storage = "double"
        elif fun is length:
            template = 0
            storage = "integer"
        elif fun is sum:
            storage = "integer" if source_storage in ("integer", "logical") else "double"
            template = 0 if storage == "integer" else 0.0
        else:
            template = _invoke(fun, [], args, kwargs)
            storage = _storage_of(template)
    else:
        template = fill
        storage = _storage_of(template)
        if fun is mean and storage == "logical":
            storage = "double"
    ordered = []
    for bucket in buckets:
        if not bucket:
            ordered.append(_coerce(template, storage))
            continue
        extracted = [values[index] for index in bucket]
        ordered.append(_coerce(_invoke(fun, extracted, args, kwargs), storage))
    return ordered, storage


def _place(values: list[Any], groups: list[int], total: int, storage: str, fill: Any) -> tuple[list[Any], str]:
    placed: list[Any] = [None] * total
    for index, group in enumerate(groups):
        placed[group - 1] = values[index]
    if fill is not _NULL:
        result_storage = _storage_of(fill)
        if result_storage == "double" or storage == "double":
            storage = "double"
        elif result_storage == "character" or storage == "character":
            storage = "character"
        placed = [
            _coerce(fill, storage) if _missing_value(value, storage) else _coerce(value, storage)
            for value in placed
        ]
    return placed, storage


def _columns_from_linear(ordered: list[Any], storage: str, n_row: int, n_col: int, names: list[str]) -> list[tuple[str, Column]]:
    columns = []
    for index, name in enumerate(names):
        start = index * n_row
        columns.append((name, Column(storage, ordered[start : start + n_row])))
    return columns


def dcast(
    data: Any,
    formula: Any,
    fun_aggregate: Any = None,
    *args: Any,
    **kwargs: Any,
) -> DataFrame:
    """Cast ``data`` to a data frame.

    ``formula`` is ``"row ~ column"`` or a list of variable-name groups.
    ``fun_aggregate`` is a function of one cell, or ``"mean"``, ``"sum"``,
    or ``"length"``. ``margins``, ``subset``, ``fill``, ``drop``, and
    ``value.var`` are keyword arguments, as they are after ``...`` in R.
    """

    if "value_var" in kwargs:
        raise ValueError("Please use value.var instead of value_var.")
    named = kwargs.pop("fun.aggregate", _MISSING)
    named_under = kwargs.pop("fun_aggregate", _MISSING)
    if named is not _MISSING:
        fun_aggregate = named
    elif named_under is not _MISSING:
        fun_aggregate = named_under
    margins = kwargs.pop("margins", None)
    subset = kwargs.pop("subset", None)
    fill = kwargs.pop("fill", _NULL)
    drop = kwargs.pop("drop", True)
    value_var = kwargs.pop("value.var", _MISSING)
    frame = _as_frame(data)
    if subset is not None:
        if callable(subset):
            mask = list(subset(frame))
        else:
            mask = list(subset)
        frame = _filter(frame, mask)
    if value_var is _MISSING:
        value_var = _guess_value(frame)
    else:
        value_var = str(value_var)
    dims = _parse_formula(formula, frame.names(), value_var)
    if len(dims) > 2:
        raise ValueError("Dataframes have at most two output dimensions")
    if len(dims) < 2:
        raise IndexError("subscript out of bounds")
    if margins is not None and margins is not False:
        frame = _add_margins(frame, dims, margins)
    if value_var not in frame.names():
        raise ValueError(f"value.var ({value_var}) not found in input")
    groups = []
    for dim in dims:
        groups.append([] if not dim else [_lookup(frame, name) for name in dim])
    value_column = _lookup(frame, value_var)
    nrows = frame.nrows
    identified = []
    empty = []
    for columns in groups:
        ids, count = _identify(columns, bool(drop))
        if len(ids) == 0:
            identified.append(([1] * nrows, 1))
            empty.append(True)
        else:
            identified.append((ids, count))
            empty.append(False)
    label_sets = []
    for columns, (ids, _count), is_empty, names in zip(groups, identified, empty, dims):
        if is_empty:
            label_sets.append([(".", Column("character", ["."]))])
        else:
            pieces = _split_labels(columns, ids, bool(drop))
            label_sets.append(list(zip(names, pieces)))
    overall, total = _combine_dimensions(identified)
    fun = _resolve_fun(fun_aggregate)
    duplicated = False
    seen: set[int] = set()
    for group in overall:
        if group in seen:
            duplicated = True
            break
        seen.add(group)
    if duplicated or fun is not None:
        if fun is None:
            sys.stderr.write("Aggregation function missing: defaulting to length\n")
            fun = length
        source, source_storage = _cell_values(value_column)
        if fun is mean or fun is sum:
            source = list(value_column.values) if not is_factor(value_column) else source
        ordered, storage = _aggregate(source, overall, total, fun, args, kwargs, fill, value_column.storage)
    else:
        source, storage = _cell_values(value_column)
        ordered, storage = _place(source, overall, total, storage, fill)
    n_row = identified[0][1]
    n_col = identified[1][1]
    if len(label_sets[0][0][1]) != n_row:
        raise ValueError("nrow(res$labels[[1]]) == nrow(data) is not TRUE")
    right = [column for _name, column in label_sets[1]]
    value_names = [_paste_row(right, row) for row in range(len(right[0]))]
    if len(value_names) != n_col:
        raise ValueError("subscript out of bounds")
    columns = list(label_sets[0])
    columns.extend(_columns_from_linear(ordered, storage, n_row, n_col, value_names))
    return DataFrame(columns)
