"""Merge, bind, and stack zoo series.

Numeric indexes are aligned by value. A matrix is stored in Fortran order.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from zoo.series import Zoo


def merge_zoo(
    *args: Any,
    all: Any = True,
    fill: Any = np.nan,
    suffixes: Any = None,
    check_names: bool = False,
    retclass: str | None = "zoo",
    drop: bool = True,
    sep: str = ".",
) -> Any:
    """Align series on the union or the intersection of their indexes."""
    if len(args) == 0:
        raise ValueError("argument is of length zero")
    retclass = _match_arg(retclass, ("zoo", "list", "data.frame"))
    args_list = [arg for arg in args if arg is not None]
    if len(args_list) == 0:
        raise ValueError("argument is of length zero")

    _check_plain_shapes(args_list)
    originals = list(args_list)
    args_list = _coerce_args(args_list)
    _reject_duplicate_indexes(args_list)

    if suffixes is None:
        suffixes = [f"X{i}" for i in range(1, len(args_list) + 1)]
    else:
        suffixes = [str(item) for item in np.atleast_1d(suffixes)]
        if len(suffixes) != len(args_list):
            warnings.warn(
                "length of suffixes and does not match number of merged objects",
                stacklevel=2,
            )
            suffixes = _recycle(suffixes, len(args_list))

    all_flags = _recycle_logical(all, len(args_list))
    index_list = [_numeric_index(arg) for arg in args_list]
    indexes = _result_index(index_list, all_flags)
    frequency = _merged_frequency(args_list)

    use_fill = bool(np.any(all_flags))
    aligned = [
        _place(
            arg,
            indexes,
            fill,
            ret_zoo=retclass in ("list", "data.frame", None),
            use_fill=use_fill,
            frequency=frequency,
        )
        for arg in args_list
    ]

    if retclass is None:
        for original, placed in zip(originals, aligned):
            if isinstance(original, Zoo) and isinstance(placed, Zoo):
                original.data = placed.data
                original.index = placed.index
                original.frequency = placed.frequency
                if getattr(placed, "columns", None) is not None:
                    original.columns = list(placed.columns)
        return None
    if retclass == "list":
        return dict(zip(suffixes, aligned))
    if retclass == "data.frame":
        return _as_frame(aligned, suffixes, indexes, sep)

    pieces = [item for item in aligned if _length(item) > 0]
    if len(pieces) > 1 or (len(pieces) == 1 and not drop):
        result = _cbind_arrays(pieces)
    elif len(pieces) == 1:
        result = np.asarray(pieces[0], dtype=float)
    else:
        result = np.array([], dtype=float)

    if result.ndim == 0:
        result = result.reshape(1)
    if result.ndim == 1:
        return _pack(result, indexes, frequency)

    names = _column_names(args_list, suffixes, sep, check_names, result.shape[1])
    return _pack(result, indexes, frequency, names)


def cbind_zoo(
    *args: Any,
    all: Any = True,
    fill: Any = np.nan,
    suffixes: Any = None,
    drop: bool = False,
    sep: str = ".",
) -> Any:
    """Bind series by column. One series stays a one-column matrix."""
    return merge_zoo(
        *args,
        all=all,
        fill=fill,
        suffixes=suffixes,
        retclass="zoo",
        drop=drop,
        sep=sep,
    )


def rbind_zoo(*args: Any, deparse_level: int = 1) -> Zoo:
    """Stack series by row. Indexes must not overlap."""
    del deparse_level
    args_list = [arg for arg in args if arg is not None]
    if len(args_list) == 0:
        raise ValueError("argument is of length zero")
    for arg in args_list:
        if not isinstance(arg, Zoo):
            raise TypeError("arguments must be zoo series")
        data = _values(arg)
        if data.ndim == 1 and data.size == 0 and len(np.asarray(arg.index)) > 0:
            raise ValueError("zero-length vectors with non-zero-length index are not allowed")

    indexes = np.concatenate([_numeric_index(arg) for arg in args_list])
    if _max_repeat(indexes) > 1:
        raise ValueError("indexes overlap")

    ncols = [_ncol(arg) for arg in args_list]
    if any(count != ncols[0] for count in ncols):
        raise ValueError("number of columns differ")

    columns = _rbind_columns(args_list)
    blocks = [_rbind_block(arg, columns) for arg in args_list]
    frequency = _merged_frequency(args_list)
    if ncols[0] > 1 or any(block.ndim == 2 for block in blocks):
        stacked = _stack_rows(blocks)
        return _pack(stacked, indexes, frequency, columns)
    flat = np.concatenate([np.asarray(block, dtype=float).reshape(-1) for block in blocks])
    return _pack(flat, indexes, frequency)


def _match_arg(value: str | None, choices: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    text = str(value)
    matches = [choice for choice in choices if choice.startswith(text)]
    if len(matches) == 1:
        return matches[0]
    quoted = ", ".join(repr(choice) for choice in choices)
    raise ValueError(f"{text!r} should be one of {quoted}")


def _check_plain_shapes(args: list[Any]) -> None:
    first = args[0]
    first_rows = _nrow(first)

    def ok(arg: Any) -> bool:
        if isinstance(arg, Zoo) or not _is_plain(arg):
            return True
        return _is_scalar(arg) or _nrow(arg) == first_rows

    if not all(ok(arg) for arg in args):
        raise ValueError(
            "plain arguments must be length 1 or have the same number of rows as the first argument"
        )


def _is_plain(obj: Any) -> bool:
    if isinstance(obj, Zoo):
        return False
    if isinstance(obj, (str, bytes, bool, int, float, np.number)):
        return True
    if isinstance(obj, np.ndarray):
        return obj.dtype.kind in "iufbOSU"
    if isinstance(obj, (list, tuple)):
        return True
    return False


def _is_scalar(obj: Any) -> bool:
    if not _is_plain(obj):
        return False
    if isinstance(obj, (str, bytes)):
        return True
    if isinstance(obj, (bool, int, float, np.number)):
        return True
    return _length(obj) == 1


def _coerce_args(args: list[Any]) -> list[Zoo]:
    coerced: list[Any] = []
    for arg in args:
        if isinstance(arg, Zoo):
            coerced.append(arg)
        elif _is_plain(arg):
            coerced.append(arg)
        else:
            raise TypeError("cannot coerce argument to a zoo series")
    if not isinstance(coerced[0], Zoo):
        coerced[0] = _plain_zoo(coerced[0], _default_index(coerced[0]), None)
    base_index = np.asarray(coerced[0].index)
    base_frequency = coerced[0].frequency
    out: list[Zoo] = []
    for arg in coerced:
        if isinstance(arg, Zoo):
            out.append(arg)
        else:
            out.append(_plain_zoo(arg, base_index, base_frequency))
    return out


def _plain_zoo(data: Any, index: Any, frequency: float | None) -> Zoo:
    index_arr = np.asarray(index)
    if index_arr.ndim == 0:
        index_arr = index_arr.reshape(1)
    order = _order(index_arr)
    index_arr = index_arr[order]
    values = np.asarray(data)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim == 1:
        if values.size == 0:
            filled = np.array([], dtype=float)
        else:
            filled = np.resize(np.asarray(values, dtype=float), index_arr.size)[order]
        return Zoo(filled, index_arr, frequency=frequency)
    rows = np.resize(np.arange(values.shape[0]), index_arr.size)
    matrix = np.array(values[rows, :], dtype=float, order="F")[order, :]
    matrix = np.asfortranarray(matrix)
    obj = Zoo(matrix, index_arr, frequency=frequency)
    columns = getattr(data, "columns", None)
    if columns is not None:
        obj.columns = list(columns)
    return obj


def _default_index(obj: Any) -> np.ndarray:
    return np.arange(1, _nrow(obj) + 1, dtype=float)


def _reject_duplicate_indexes(args: list[Zoo]) -> None:
    for arg in args:
        index = _numeric_index(arg)
        if index.size and len(set(_keys(index))) < index.size:
            raise ValueError("series cannot be merged with non-unique index entries in a series")


def _result_index(index_list: list[np.ndarray], all_flags: np.ndarray) -> np.ndarray:
    chosen = [index_list[i] for i, flag in enumerate(all_flags) if flag]
    intersection = _intersection(index_list)
    if not chosen:
        return intersection
    parts = chosen + ([intersection] if intersection.size else [])
    return _sort_unique(np.concatenate(parts))


def _intersection(index_list: list[np.ndarray]) -> np.ndarray:
    if not index_list:
        return np.array([], dtype=float)
    counts: dict[float, int] = {}
    for index in index_list:
        for key in dict.fromkeys(_keys(index)):
            counts[key] = counts.get(key, 0) + 1
    needed = len(index_list)
    found = [key for key, count in counts.items() if count == needed]
    if not found:
        return np.array([], dtype=float)
    return np.sort(np.asarray(found, dtype=float))


def _sort_unique(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return np.array([], dtype=float)
    first: dict[float, float] = {}
    for value in np.asarray(values, dtype=float):
        key = float(value)
        if key not in first:
            first[key] = key
    return np.sort(np.fromiter(first.values(), dtype=float, count=len(first)))


def _place(
    arg: Zoo,
    indexes: np.ndarray,
    fill: Any,
    ret_zoo: bool,
    use_fill: bool,
    frequency: float | None,
) -> Any:
    data = _values(arg)
    index = _numeric_index(arg)
    if not use_fill:
        return _take(arg, data, index, indexes, ret_zoo, frequency)
    if data.ndim == 1 and data.size == 0:
        if ret_zoo:
            return _pack(np.array([], dtype=float), indexes, frequency)
        return np.array([], dtype=float)
    into_source = _match(indexes, index)
    found = into_source > 0
    rows = np.flatnonzero(found)
    if data.ndim == 1:
        placed = np.full(indexes.size, fill, dtype=float)
        placed[rows] = np.asarray(data, dtype=float)[into_source[found] - 1]
        if ret_zoo:
            return _pack(placed, indexes, frequency)
        return placed
    placed = np.full((indexes.size, data.shape[1]), fill, dtype=float, order="F")
    placed[rows, :] = np.asarray(data, dtype=float)[into_source[found] - 1, :]
    placed = np.asfortranarray(placed)
    if ret_zoo:
        return _pack(placed, indexes, frequency, getattr(arg, "columns", None))
    return placed


def _take(
    arg: Zoo,
    data: np.ndarray,
    index: np.ndarray,
    indexes: np.ndarray,
    ret_zoo: bool,
    frequency: float | None,
) -> Any:
    if data.ndim == 1 and data.size == 0:
        if ret_zoo:
            return _pack(np.array([], dtype=float), indexes, frequency)
        return np.array([], dtype=float)
    positions = _match(indexes, index)
    keep = positions[positions > 0] - 1
    if data.ndim == 1:
        taken = np.asarray(data, dtype=float)[keep]
        if ret_zoo:
            return _pack(taken, indexes, frequency)
        return taken
    taken = np.asfortranarray(np.asarray(data, dtype=float)[keep, :])
    columns = getattr(arg, "columns", None)
    if ret_zoo:
        return _pack(taken, indexes, frequency, columns)
    return taken


def _column_names(
    args: list[Zoo],
    suffixes: list[str],
    sep: str,
    check_names: bool,
    result_ncol: int,
) -> list[str] | None:
    # The installed loop leaves i at the last argument. An unnamed matrix
    # in the named branch reads that last suffix.
    last = len(args)
    collected = [_stored_columns(arg) for arg in args]
    if any(names for names in collected):
        groups = [_fix_named(arg, suffixes, sep, last) for arg in args]
        flat = _flatten(groups)
        duplicated = _duplicated_values(flat)
        fixme = []
        for group in groups:
            if group is None:
                fixme.append(None)
            else:
                fixme.append([name in duplicated for name in group])
        groups = [_blank_to_suffix(group, suffixes[i]) for i, group in enumerate(groups)]
        if _has_duplicate(_flatten(groups)):
            groups = [
                _paste_fixed(group, suffixes[i], sep, flags)
                for i, (group, flags) in enumerate(zip(groups, fixme))
            ]
    else:
        groups = [_fix_plain(arg, sep) for arg in args]
        groups = [
            None if group is None else [suffixes[i] + name for name in group]
            for i, group in enumerate(groups)
        ]
    flat = _flatten(groups)
    if check_names:
        return _make_names(_make_unique(flat))
    if result_ncol == len(flat):
        return flat
    return None


def _fix_named(arg: Zoo, suffixes: list[str], sep: str, last: int) -> list[str] | None:
    data = _values(arg)
    if data.ndim == 1:
        if data.size == 0:
            return None
        return [""]
    if data.shape[1] == 0:
        return None
    names = _stored_columns(arg)
    if names is None:
        suffix = suffixes[last - 1]
        return [f"{number}{sep}{suffix}" for number in range(1, data.shape[1] + 1)]
    out = []
    for pos, name in enumerate(names, start=1):
        out.append(str(pos) if name == "" else name)
    return out


def _fix_plain(arg: Zoo, sep: str) -> list[str] | None:
    data = _values(arg)
    if _length(data) == 0:
        return None
    count = 1 if data.ndim == 1 else data.shape[1]
    if count < 2:
        return [""]
    return [f"{sep}{number}" for number in range(1, count + 1)]


def _blank_to_suffix(group: list[str] | None, suffix: str) -> list[str] | None:
    if group is None:
        return None
    return [suffix if name == "" else name for name in group]


def _paste_fixed(
    group: list[str] | None,
    suffix: str,
    sep: str,
    flags: list[bool] | None,
) -> list[str] | None:
    if group is None or flags is None:
        return None
    return [f"{name}{sep}{suffix}" if flag else name for name, flag in zip(group, flags)]


def _duplicated_values(names: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for name in names:
        if name in seen:
            duplicated.add(name)
        else:
            seen.add(name)
    return duplicated


def _has_duplicate(names: list[str]) -> bool:
    return len(names) != len(set(names))


def _flatten(groups: list[list[str] | None]) -> list[str]:
    flat: list[str] = []
    for group in groups:
        if group is not None:
            flat.extend(group)
    return flat


def _make_unique(names: list[str]) -> list[str]:
    used: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in used:
            used.add(name)
            out.append(name)
            continue
        number = 1
        candidate = f"{name}.{number}"
        while candidate in used:
            number += 1
            candidate = f"{name}.{number}"
        used.add(candidate)
        out.append(candidate)
    return out


def _make_names(names: list[str]) -> list[str]:
    out = []
    for name in names:
        cleaned = "".join(char if char.isalnum() or char == "." else "." for char in name)
        if not cleaned or cleaned[0].isdigit() or (cleaned[0] == "." and len(cleaned) > 1 and cleaned[1].isdigit()):
            cleaned = "X" + cleaned
        if cleaned in {"if", "else", "repeat", "while", "function", "for", "in", "next", "break"}:
            cleaned = cleaned + "."
        out.append(cleaned)
    return out


def _rbind_columns(args: list[Zoo]) -> list[str] | None:
    groups = [_stored_columns(arg) for arg in args]
    if all(group is None for group in groups):
        return None
    if any(group is None for group in groups):
        warnings.warn("column names differ", stacklevel=3)
        return groups[0]
    first = list(groups[0])
    if all(group == first for group in groups):
        return first
    if all(sorted(group) == sorted(first) for group in groups):
        return first
    warnings.warn("column names differ", stacklevel=3)
    return groups[0]


def _rbind_block(arg: Zoo, columns: list[str] | None) -> np.ndarray:
    data = np.asarray(_values(arg), dtype=float)
    own = _stored_columns(arg)
    vector = data.ndim == 1
    if columns is not None and own is not None and own != list(columns) and sorted(own) == sorted(columns):
        positions = [own.index(name) for name in columns]
        if vector:
            data = data.reshape(-1, 1)
            vector = False
        data = np.asfortranarray(data[:, positions])
    if data.ndim == 1:
        return data
    return np.asfortranarray(data)


def _stack_rows(blocks: list[np.ndarray]) -> np.ndarray:
    prepared = []
    for block in blocks:
        array = np.asarray(block, dtype=float)
        if array.ndim == 1:
            array = array.reshape(-1, 1)
        prepared.append(array)
    total = sum(array.shape[0] for array in prepared)
    width = prepared[0].shape[1]
    stacked = np.empty((total, width), dtype=float, order="F")
    row = 0
    for array in prepared:
        count = array.shape[0]
        stacked[row : row + count, :] = array
        row += count
    return stacked


def _cbind_arrays(pieces: list[Any]) -> np.ndarray:
    columns = []
    for piece in pieces:
        array = np.asarray(piece, dtype=float)
        if array.ndim == 1:
            columns.append(array.reshape(-1, 1))
        else:
            columns.append(array)
    rows = columns[0].shape[0]
    width = sum(array.shape[1] for array in columns)
    bound = np.empty((rows, width), dtype=float, order="F")
    col = 0
    for array in columns:
        count = array.shape[1]
        bound[:, col : col + count] = array
        col += count
    return bound


def _as_frame(aligned: list[Any], suffixes: list[str], indexes: np.ndarray, sep: str) -> dict[str, Any]:
    columns: dict[str, np.ndarray] = {}
    for suffix, item in zip(suffixes, aligned):
        data = _values(item) if isinstance(item, Zoo) else np.asarray(item, dtype=float)
        if data.ndim <= 1:
            columns[suffix] = np.asarray(data, dtype=float).reshape(-1)
            continue
        names = _stored_columns(item) if isinstance(item, Zoo) else None
        for number in range(data.shape[1]):
            name = names[number] if names is not None else f"{suffix}{sep}{number + 1}"
            columns[name] = np.asarray(data[:, number], dtype=float)
    return {"index": np.asarray(indexes, dtype=float), "columns": columns}


def _merged_frequency(args: list[Zoo]) -> float | None:
    present = [arg.frequency for arg in args if getattr(arg, "frequency", None) is not None]
    if len(present) != len(args) or not present:
        return None
    largest = max(present)
    ratios = [largest / freq for freq in present]
    if all(abs(ratio - round(ratio)) <= 1e-8 for ratio in ratios):
        return float(largest)
    return None


def _pack(
    data: np.ndarray,
    index: np.ndarray,
    frequency: float | None,
    columns: list[str] | None = None,
) -> Zoo:
    values = np.asarray(data, dtype=float)
    order = _order(index)
    sorted_index = np.asarray(index, dtype=float)[order]
    if values.ndim == 0:
        values = values.reshape(1)
    if values.size == 0 and values.ndim == 1:
        obj = Zoo(np.array([], dtype=float), sorted_index, frequency=frequency)
    elif values.ndim == 1:
        obj = Zoo(values[order], sorted_index, frequency=frequency)
    else:
        obj = Zoo(np.asfortranarray(values[order, :]), sorted_index, frequency=frequency)
        if columns is not None:
            obj.columns = list(columns)
    return obj


def _values(obj: Any) -> np.ndarray:
    data = obj.data if isinstance(obj, Zoo) else np.asarray(obj)
    array = np.asarray(data)
    if array.ndim == 0:
        return array.reshape(1)
    return array


def _stored_columns(obj: Any) -> list[str] | None:
    if not isinstance(obj, Zoo):
        return None
    columns = getattr(obj, "columns", None)
    if columns is None:
        return None
    return [str(name) for name in columns]


def _numeric_index(obj: Zoo) -> np.ndarray:
    index = np.asarray(obj.index, dtype=float)
    if index.ndim == 0:
        return index.reshape(1)
    return index


def _nrow(obj: Any) -> int:
    if isinstance(obj, Zoo):
        data = _values(obj)
    else:
        data = np.asarray(obj)
        if data.ndim == 0:
            return 1
    if data.ndim == 0:
        return 1
    return int(data.shape[0])


def _ncol(obj: Any) -> int:
    data = _values(obj) if isinstance(obj, Zoo) else np.asarray(obj)
    if getattr(data, "ndim", 0) <= 1:
        return 1
    return int(data.shape[1])


def _length(obj: Any) -> int:
    array = _values(obj) if isinstance(obj, Zoo) else np.asarray(obj)
    return int(np.asarray(array).size)


def _order(index: np.ndarray) -> np.ndarray:
    values = np.asarray(index, dtype=float)
    if values.ndim == 0:
        return np.array([0])
    return np.argsort(values, kind="mergesort")


def _keys(values: np.ndarray) -> list[float]:
    return [float(value) for value in np.asarray(values, dtype=float).reshape(-1)]


def _match(needles: np.ndarray, haystack: np.ndarray) -> np.ndarray:
    table: dict[float, int] = {}
    for position, value in enumerate(_keys(haystack), start=1):
        table.setdefault(value, position)
    return np.asarray([table.get(value, 0) for value in _keys(needles)], dtype=int)


def _max_repeat(values: np.ndarray) -> int:
    counts: dict[float, int] = {}
    best = 0
    for key in _keys(values):
        counts[key] = counts.get(key, 0) + 1
        best = max(best, counts[key])
    return best


def _recycle(items: list[str], size: int) -> list[str]:
    if not items:
        raise ValueError("replacement has length zero")
    return [items[i % len(items)] for i in range(size)]


def _recycle_logical(value: Any, size: int) -> np.ndarray:
    flags = np.atleast_1d(np.asarray(value, dtype=bool)).reshape(-1)
    if flags.size == 0:
        raise ValueError("argument is of length zero")
    return np.resize(flags, size)
