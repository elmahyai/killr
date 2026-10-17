"""zoo constructor and the methods defined with it.

NumPy holds the values. A matrix is stored in Fortran order.
"""

from __future__ import annotations

import math
import operator
import sys
import warnings
from typing import Any

import numpy as np

from zoo.series import Zoo

_EPS = float(np.finfo(float).eps)
_TOL = math.sqrt(_EPS)


def is_zoo(object: Any) -> bool:
    """True when ``object`` is a zoo series, including a regular one."""
    return isinstance(object, Zoo)


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, np.bool_)):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isnan(number)


def _key(value: Any) -> tuple:
    if _is_na(value):
        return ("na",)
    if isinstance(value, (str, np.str_)):
        return ("s", str(value))
    try:
        return ("n", float(value))
    except (TypeError, ValueError):
        return ("o", str(value))


def _as_float_array(values: Any) -> np.ndarray:
    if is_zoo(values):
        values = values.data
    if values is None:
        return np.array([], dtype=float)
    array = np.asarray(values)
    if array.dtype == object or array.dtype.kind == "O":
        flat = []
        for item in array.ravel(order="F"):
            flat.append(np.nan if _is_na(item) else float(item))
        return np.asarray(flat, dtype=float).reshape(array.shape, order="F")
    if array.dtype.kind == "b":
        return array.astype(float)
    return np.array(array, dtype=float, copy=True)


def _all_equal(target: Any, current: Any) -> bool:
    """R's ``identical(all.equal(target, current), TRUE)`` for numeric vectors."""
    left = np.asarray(target, dtype=float).ravel()
    right = np.asarray(current, dtype=float).ravel()
    if left.shape != right.shape:
        return False
    if left.size == 0:
        return True
    if np.any(np.isnan(left)) or np.any(np.isnan(right)):
        return False
    xy = float(np.mean((left - right) ** 2))
    xn = float(np.mean(left ** 2))
    if math.isfinite(xn) and xn > _TOL:
        xy = xy / xn
    return xy <= _TOL ** 2


def _order_positions(index: Any) -> np.ndarray:
    """0-based stable order, with missing values last. This is R's ``ORDER``."""
    values = list(np.asarray(index, dtype=object) if np.asarray(index).dtype == object else np.asarray(index))
    if isinstance(index, np.ndarray) and index.dtype != object:
        values = list(index)
    decorated = []
    for position, value in enumerate(values):
        if _is_na(value):
            decorated.append((1, 0.0, position))
        else:
            try:
                decorated.append((0, float(value), position))
            except (TypeError, ValueError):
                decorated.append((0, str(value), position))
    decorated.sort(key=lambda item: (item[0], item[1], item[2]))
    return np.asarray([item[2] for item in decorated], dtype=int)


def _match_self(values: Any) -> np.ndarray:
    """1-based positions of the first match, as ``MATCH(x, x)``."""
    array = np.asarray(values)
    first: dict[tuple, int] = {}
    codes = np.empty(array.size, dtype=float)
    for position, value in enumerate(array.ravel(order="F")):
        key = _key(value)
        if key not in first:
            first[key] = position + 1
        codes[position] = first[key]
    return codes


def _my_unique(values: Any) -> np.ndarray:
    array = np.asarray(values)
    codes = _match_self(array)
    kept = [array.ravel()[i] for i, code in enumerate(codes) if code == i + 1]
    if not kept:
        return np.array([], dtype=float)
    try:
        return np.asarray(kept, dtype=float)
    except (TypeError, ValueError):
        return np.asarray(kept, dtype=object)


def _gcd0(left: int, right: int) -> int:
    left, right = abs(int(left)), abs(int(right))
    while right != 0 and left != right:
        left, right = right, left % right
    return left


def _gcd_many(values: np.ndarray) -> int:
    numbers = [int(round(float(value))) for value in np.asarray(values).ravel()]
    if len(numbers) < 2:
        numbers = numbers + [0]
    if len(numbers) < 3:
        return _gcd0(numbers[0], numbers[1])
    reduced = [_gcd0(numbers[i], numbers[i + 1]) for i in range(len(numbers) - 1)]
    return _gcd_many(np.asarray(reduced))


def _unique_in_order(values: np.ndarray) -> np.ndarray:
    seen = set()
    kept = []
    for value in np.asarray(values).ravel():
        key = _key(value)
        if key in seen:
            continue
        seen.add(key)
        kept.append(value)
    return np.asarray(kept, dtype=float)


def frequency_of(x: Zoo) -> float | None:
    """``frequency.zoo`` for a series whose frequency was not stored."""
    freq = x.frequency
    index = np.asarray(x.index, dtype=float)
    if freq is not None or index.size < 2:
        return None if freq is None else float(freq)
    delta = np.diff(index)
    if np.any(np.isnan(delta)):
        return None
    distinct = _unique_in_order(delta)
    smallest = float(np.min(distinct))
    if smallest == 0:
        return None
    if _all_equal(distinct / smallest, np.round(distinct / smallest)):
        freq = 1.0 / smallest
    elif _all_equal(distinct, np.round(distinct)):
        freq = 1.0 / _gcd_many(distinct)
    else:
        return None
    if freq > 1 and _all_equal(freq, round(freq)):
        freq = float(round(freq))
    return float(freq)


def _plain_numeric(index: np.ndarray) -> bool:
    if index.dtype.kind not in "iuf":
        return False
    return True


def zoo(
    x: Any = None,
    order_by: Any = None,
    frequency: float | None = None,
    calendar: bool = True,
) -> Zoo:
    """Create an ordered series. Observations are sorted by ``order_by``."""
    if is_zoo(x) and order_by is None:
        order_by = np.array(x.index, copy=True)
        source = x.data
    elif order_by is None:
        if x is None:
            order_by = np.array([], dtype=int)
            source = None
        else:
            source = x
            probed = np.asarray(x)
            nrow = probed.shape[0] if probed.ndim >= 1 else 1
            order_by = np.arange(1, nrow + 1)
    else:
        source = None if x is None else (x.data if is_zoo(x) else x)
        order_by = np.array(order_by, copy=True)

    if order_by.ndim > 1:
        order_by = order_by.ravel(order="F")
    if _match_self(order_by).size and len(set(_match_self(order_by).tolist())) < order_by.size:
        warnings.warn(
            "some methods for “zoo” objects do not work if the index entries in ‘order.by’ are not unique",
            stacklevel=2,
        )
    permutation = _order_positions(order_by)
    order_by = order_by[permutation]

    matrix = False
    if source is not None:
        array = np.asarray(source)
        if array.ndim == 2 and int(array.shape[0] + array.shape[1]) < 1:
            source = None
            array = None
        elif array.ndim == 2:
            matrix = True
    if source is None:
        data = np.array([], dtype=float)
    elif matrix:
        array = np.array(np.asarray(source), dtype=float, order="F", copy=True)
        nrow = array.shape[0]
        n = int(order_by.size)
        if n == 0:
            data = array[:0, :]
        elif nrow == 0:
            data = np.zeros((n, array.shape[1]), dtype=float, order="F")
        else:
            rows = np.resize(np.arange(nrow), n)[permutation]
            data = np.array(array[rows, :], order="F", copy=True)
    else:
        try:
            flat = _as_float_array(source).ravel(order="F")
        except (TypeError, ValueError) as error:
            raise ValueError("“x” : attempt to define invalid zoo object") from error
        n = int(order_by.size)
        if flat.size == 0 and n == 0:
            data = flat
        elif source is None:
            data = np.array([], dtype=float)
        else:
            if flat.size == 0:
                data = np.array([], dtype=float)
            else:
                data = np.array(np.resize(flat, n)[permutation], dtype=float, copy=True)

    freq: float | None = None if frequency is None else float(frequency)
    if freq is not None and _plain_numeric(np.asarray(order_by)):
        numeric_index = np.asarray(order_by, dtype=float)
        delta = np.diff(numeric_index)
        if delta.size and (np.any(np.isnan(delta)) or not _all_equal(delta * freq, np.round(delta * freq))):
            warnings.warn(
                "“order.by” and “frequency” do not match: “frequency” ignored",
                stacklevel=2,
            )
            freq = None
        elif delta.size == 0 or _all_equal(delta * freq, np.round(delta * freq)):
            if freq > 1 and _all_equal(freq, round(freq)):
                freq = float(round(freq))
            snapped = np.floor(freq * numeric_index + 0.0001) / freq
            if _all_equal(snapped, numeric_index):
                numeric_index = snapped
            if calendar and freq in (4, 12):
                if freq == 4:
                    numeric_index = np.floor(4 * numeric_index + 0.001) / 4
                else:
                    numeric_index = np.floor(12 * numeric_index + 0.0001) / 12
            order_by = numeric_index
        else:
            freq = None

    series = Zoo(data, order_by, frequency=freq, regular=freq is not None)
    if matrix and isinstance(source, np.ndarray) is False:
        pass
    return series


def _copy_flags(source: Zoo, target: Zoo) -> Zoo:
    target.colnames = None if source.colnames is None else list(source.colnames)
    target.logical = bool(source.logical)
    target.extra = dict(source.extra)
    return target


def coredata(x: Any) -> np.ndarray:
    if is_zoo(x):
        return x.data
    return np.asarray(x)


def index(x: Any) -> np.ndarray:
    if is_zoo(x):
        return np.asarray(x.index)
    array = np.asarray(x)
    nrow = array.shape[0] if array.ndim >= 1 else 1
    return np.arange(1, nrow + 1)


def time(x: Any) -> np.ndarray:
    return index(x)


def _nrow(x: Zoo) -> int:
    data = x.data
    if data.ndim == 0:
        return 1
    return int(data.shape[0])


def _is_matrix(x: Zoo) -> bool:
    return x.data.ndim == 2


def _subset_rows(x: Zoo, positions: Any, drop: bool = True) -> Zoo:
    positions = np.asarray(list(positions), dtype=int)
    data = x.data
    idx = np.asarray(x.index)[positions] if positions.size or np.asarray(x.index).size else np.asarray(x.index)[:0]
    if positions.size == 0:
        idx = np.asarray(x.index)[:0]
    if data.ndim == 1:
        new = data[positions] if data.size or positions.size == 0 else data
        if positions.size == 0:
            new = np.array([], dtype=float)
    else:
        new = data[positions, :]
        if drop and positions.size == 1:
            new = np.array(new.reshape(-1), dtype=float)
        else:
            new = np.array(new, order="F", copy=True)
    out = zoo(new, idx, frequency=x.frequency)
    out.colnames = None if x.colnames is None else list(x.colnames)
    out.logical = bool(x.logical)
    return out


def _decimals(value: float, digits: int = 7) -> int | None:
    if not math.isfinite(value):
        return None
    if abs(value - round(value)) <= 1e-10 * max(1.0, abs(value)):
        return 0
    text = format(value, f".{digits}g")
    if "e" in text or "E" in text:
        return None
    if "." not in text:
        return 0
    return len(text.split(".")[1])


def _needs_sci(value: float) -> bool:
    if value == 0 or not math.isfinite(value):
        return False
    exponent = math.floor(math.log10(abs(value)))
    return exponent >= 5 or exponent < -4


def _scientific(value: float) -> str:
    if value == 0:
        return "0e+00"
    sign = "-" if math.copysign(1.0, value) < 0 and value != 0 else ""
    exponent = math.floor(math.log10(abs(value)))
    mantissa = abs(value) / (10 ** exponent)
    text = format(mantissa, ".6g")
    if text.startswith("10"):
        mantissa = float(text) / 10
        exponent += 1
        text = format(mantissa, ".6g")
    return f"{sign}{text}e{exponent:+03d}"


def r_format_numeric(values: Any) -> list[str]:
    """Format a numeric vector the way R's ``format`` does for printing."""
    array = _as_float_array(values).ravel(order="F")
    cells: list[str] = []
    finite = [float(value) for value in array if not math.isnan(value)]
    if not finite:
        cells = ["NA" for _ in array]
    else:
        decs = [_decimals(value) for value in finite]
        scientific = any(item is None or _needs_sci(value) for item, value in zip(decs, finite))
        texts: list[str] = []
        if scientific:
            for value in array:
                if math.isnan(value):
                    texts.append("NA")
                else:
                    texts.append(_scientific(float(value)))
        else:
            places = max(int(item) for item in decs if item is not None)
            for value in array:
                if math.isnan(value):
                    texts.append("NA")
                elif places == 0:
                    texts.append(str(int(round(float(value)))))
                else:
                    texts.append(f"{float(value):.{places}f}")
        cells = texts
    width = max((len(cell) for cell in cells), default=0)
    return [cell.rjust(width) for cell in cells]


def r_format_logical(values: Any) -> list[str]:
    array = _as_float_array(values).ravel(order="F")
    cells = []
    for value in array:
        if math.isnan(value):
            cells.append("NA")
        elif value != 0:
            cells.append("TRUE")
        else:
            cells.append("FALSE")
    width = max((len(cell) for cell in cells), default=0)
    return [cell.rjust(width) for cell in cells]


def _format_cells(x: Zoo) -> list[str]:
    if x.logical:
        return r_format_logical(x.data)
    return r_format_numeric(x.data if x.data.ndim == 1 else x.data.ravel(order="F"))


def index2char(index_values: Any, frequency: float | None = None, digits: int = 4) -> list[str]:
    array = np.asarray(index_values)
    if array.size == 0:
        return []
    if array.dtype.kind not in "iuf":
        return [str(value) for value in array.ravel()]
    numbers = np.asarray(array, dtype=float).ravel()
    freq = None if frequency is None else float(frequency)
    if freq is not None and numbers.size:
        delta = np.diff(numbers)
        if freq > 1 and _all_equal(freq, round(freq)):
            freq = float(round(freq))
        if delta.size == 0 or _all_equal(freq * delta, np.round(freq * delta)):
            if freq == 1:
                return ["NA" if math.isnan(value) else str(int(round(float(value)))) for value in numbers]
            labels = []
            for value in numbers:
                if math.isnan(value):
                    labels.append("NA")
                else:
                    cycle = int(round((value - math.floor(value)) * freq) + 1)
                    labels.append(f"{int(math.floor(value))}({cycle})")
            return labels
    labels = []
    for value in numbers:
        if math.isnan(value):
            labels.append("NA")
            continue
        rounded = round(float(value), digits)
        if abs(rounded - round(rounded)) < 1e-10:
            labels.append(str(int(round(rounded))))
        else:
            labels.append(format(rounded, "g"))
    return labels


def _format_named(names: list[str], formatted: list[str]) -> str:
    if not names:
        return ""
    width = max(max(len(name) for name in names), max((len(cell) for cell in formatted), default=0))
    line_names = " ".join(name.rjust(width) for name in names) + " "
    line_values = " ".join(cell.rjust(width) for cell in formatted) + " "
    return line_names + "\n" + line_values


def _format_atomic(values: Any, logical: bool = False, empty: str = "numeric(0)") -> str:
    array = np.asarray(values)
    if array.size == 0:
        return empty
    formatted = r_format_logical(array) if logical else r_format_numeric(array)
    return "[1] " + " ".join(formatted)


def _format_zoo(x: Zoo, style: str | None = None, quote: bool = False) -> str:
    del quote
    if style is None:
        style = "horizontal" if not _is_matrix(x) else "vertical"
    style = _match_arg(style, ("horizontal", "vertical", "plain"))
    if not _is_matrix(x) and _nrow(x) == 0 and np.asarray(x.data).size == 0:
        style = "plain"
    if _is_matrix(x) and style == "horizontal":
        style = "plain"
    if style == "vertical":
        return _format_vertical(x)
    if style == "plain":
        data_empty = "numeric(0)"
        index_values = np.asarray(x.index)
        if index_values.size == 0:
            index_text = "integer(0)" if getattr(index_values, "dtype", None) is not None and index_values.dtype.kind == "i" else "numeric(0)"
            if index_values.dtype.kind not in "i":
                index_text = "numeric(0)" if index_values.dtype.kind == "f" else "integer(0)"
        else:
            index_text = _format_atomic(index_values)
        data_text = _format_atomic(x.data, logical=x.logical, empty=data_empty) if not _is_matrix(x) else _format_matrix_plain(x)
        return f"Data:\n{data_text}\n\nIndex:\n{index_text}"
    names = index2char(x.index, frequency=x.frequency)
    formatted = _format_cells(x) if not _is_matrix(x) else r_format_numeric(x.data[:, 0])
    if x.logical and not _is_matrix(x):
        formatted = r_format_logical(x.data)
    return _format_named(names, formatted)


def _format_matrix_plain(x: Zoo) -> str:
    data = np.array(x.data, dtype=float, order="F")
    nrow, ncol = data.shape
    colnames = x.colnames if x.colnames is not None else [f"[,{j + 1}]" for j in range(ncol)]
    body_cols = []
    for j in range(ncol):
        body_cols.append(r_format_numeric(data[:, j]))
    row_labels = [f"[{i + 1},]" for i in range(nrow)]
    columns = [row_labels] + body_cols
    headers = [""] + list(colnames)
    widths = []
    for j, column in enumerate(columns):
        widths.append(max(len(headers[j]), max((len(cell) for cell in column), default=0)))
    lines = [" ".join(headers[j].rjust(widths[j]) for j in range(len(headers))).rstrip()]
    for i in range(nrow):
        lines.append(" ".join(columns[j][i].rjust(widths[j]) for j in range(len(columns))).rstrip())
    return "\n".join(lines)


def _format_vertical(x: Zoo) -> str:
    data = x.data if _is_matrix(x) else np.array(x.data, dtype=float).reshape(-1, 1)
    if x.logical and not _is_matrix(x):
        columns = [r_format_logical(data.ravel())]
        headers = [""]
    else:
        data = np.array(data, dtype=float, order="F")
        headers = list(x.colnames) if x.colnames else [""] * data.shape[1]
        columns = [r_format_numeric(data[:, j]) for j in range(data.shape[1])]
    row_names = index2char(x.index, frequency=x.frequency)
    if not row_names and data.shape[0] == 0:
        return ""
    name_width = max((len(name) for name in row_names), default=0)
    col_widths = [max(len(headers[j]), max((len(cell) for cell in columns[j]), default=0)) for j in range(len(columns))]
    header = " " * name_width + "".join(" " + headers[j].rjust(col_widths[j]) for j in range(len(headers)))
    lines = [header.rstrip() + (" " if header.strip() == "" else "")]
    if header.strip() == "":
        lines = [" " * (name_width + sum(col_widths) + len(col_widths))]
    else:
        lines = [header]
    for i, name in enumerate(row_names):
        pieces = [name.rjust(name_width)]
        for j in range(len(columns)):
            pieces.append(columns[j][i].rjust(col_widths[j]))
        lines.append(" ".join(pieces))
    return "\n".join(lines)


def _match_arg(arg: str, choices: tuple[str, ...] | list[str]) -> str:
    if arg in choices:
        return arg
    matches = [choice for choice in choices if choice.startswith(arg)]
    if len(matches) == 1:
        return matches[0]
    quoted = ", ".join(f'"{choice}"' for choice in choices)
    raise ValueError(f"'{arg}' should be one of {quoted}")


def print_zoo(x: Zoo, style: str | None = None, quote: bool = False, **kwargs: Any) -> Zoo:
    """Print a series. A vector is horizontal; a matrix is vertical."""
    del kwargs
    sys.stdout.write(_format_zoo(x, style=style, quote=quote) + "\n")
    return x


def _summary_column(values: np.ndarray, count_na: bool = True) -> list[tuple[str, str]]:
    flat = _as_float_array(values).ravel(order="F")
    missing = int(np.sum(np.isnan(flat)))
    present = flat[~np.isnan(flat)]
    if present.size == 0:
        stats = [("Min.", "NA"), ("1st Qu.", "NA"), ("Median", "NA"), ("Mean", "NA"), ("3rd Qu.", "NA"), ("Max.", "NA")]
    else:
        quantiles = _quantile_values(present, np.array([0.0, 0.25, 0.5, 0.75, 1.0]))
        mean = float(np.mean(present))
        labels = [quantiles[0], quantiles[1], quantiles[2], mean, quantiles[3], quantiles[4]]
        names = ["Min.", "1st Qu.", "Median", "Mean", "3rd Qu.", "Max."]
        stats = list(zip(names, [f"{value:.1f}" if math.isfinite(value) else "NA" for value in labels]))
    if count_na and missing:
        stats.append(("NA's", str(missing)))
    return stats


def summary_zoo(object: Zoo, **kwargs: Any) -> dict[str, list[tuple[str, str]]]:
    """Five-number summary of the index and of each column."""
    del kwargs
    columns: dict[str, list[tuple[str, str]]] = {}
    index_values = np.asarray(object.index, dtype=float)
    columns["Index"] = _summary_column(index_values, count_na=False)
    if _is_matrix(object):
        labels = object.colnames
        if not labels:
            labels = [f"x.{j + 1}" for j in range(object.data.shape[1])]
        for j, label in enumerate(labels):
            columns[str(label)] = _summary_column(object.data[:, j])
    else:
        columns["x"] = _summary_column(object.data)
    return columns


def _format_summary(table: dict[str, list[tuple[str, str]]]) -> str:
    names = list(table)
    blocks = []
    for name in names:
        rows = table[name]
        label_width = max(len(label) for label, _ in rows)
        value_width = max(len(value) for _, value in rows)
        line_width = max(len(name), label_width + 1 + value_width)
        header = name.rjust(line_width)
        body = []
        for label, value in rows:
            body.append(f"{label:<{label_width}}: {value:>{value_width}}".rjust(line_width))
        blocks.append((header, body, line_width))
    height = max(len(block[1]) for block in blocks)
    lines = ["  ".join(block[0] for block in blocks)]
    for row in range(height):
        pieces = []
        for _, body, width in blocks:
            pieces.append(body[row] if row < len(body) else " " * width)
        lines.append("  ".join(pieces).rstrip())
    return "\n".join(lines)


def head_zoo(x: Zoo, n: int = 6, **kwargs: Any) -> Zoo:
    """First ``n`` observations. A negative ``n`` drops that many from the end."""
    del kwargs
    n_array = np.atleast_1d(np.asarray(n))
    if n_array.size != 1:
        raise ValueError("length(n) == 1 is not TRUE")
    n_value = int(n_array[0])
    xlen = _nrow(x)
    if n_value < 0:
        n_value = max(xlen + n_value, 0)
    else:
        n_value = min(n_value, xlen)
    return _subset_rows(x, range(n_value), drop=False if _is_matrix(x) else True)


def tail_zoo(x: Zoo, n: int = 6, **kwargs: Any) -> Zoo:
    """Last ``n`` observations. A negative ``n`` drops that many from the start."""
    del kwargs
    n_array = np.atleast_1d(np.asarray(n))
    if n_array.size != 1:
        raise ValueError("length(n) == 1 is not TRUE")
    n_value = int(n_array[0])
    xlen = _nrow(x)
    if n_value < 0:
        n_value = max(xlen + n_value, 0)
    else:
        n_value = min(n_value, xlen)
    start = xlen - n_value
    return _subset_rows(x, range(start, xlen), drop=False if _is_matrix(x) else True)


def _flatten_core(*series: Any) -> np.ndarray:
    parts = []
    for item in series:
        values = coredata(item) if is_zoo(item) else item
        parts.append(_as_float_array(values).ravel(order="F"))
    if not parts:
        return np.array([], dtype=float)
    return np.concatenate(parts)


def range_zoo(*series: Any, na_rm: bool = False, **kwargs: Any) -> np.ndarray:
    """Range of the core data of one or more series."""
    del kwargs
    values = _flatten_core(*series)
    if not na_rm and np.any(np.isnan(values)):
        return np.array([np.nan, np.nan])
    present = values[~np.isnan(values)] if values.size else values
    if present.size == 0:
        return np.array([np.inf, -np.inf])
    return np.array([float(np.min(present)), float(np.max(present))])


def _scale_matrix(x: Any, center: Any = True, scale: Any = True) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    data = _as_float_array(x)
    if data.ndim == 1:
        data = np.array(data.reshape(-1, 1), order="F")
    else:
        data = np.array(data, dtype=float, order="F", copy=True)
    ncol = data.shape[1]
    center_attr = None
    scale_attr = None
    if isinstance(center, (bool, np.bool_)):
        if center:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                center_attr = np.array([np.nanmean(data[:, j]) for j in range(ncol)])
            data = data - center_attr
    else:
        center_attr = np.asarray(center, dtype=float).ravel()
        if center_attr.size != ncol:
            raise ValueError("length of 'center' must equal the number of columns of 'x'")
        data = data - center_attr
    if isinstance(scale, (bool, np.bool_)):
        if scale:
            scales = []
            for j in range(ncol):
                column = data[:, j]
                column = column[~np.isnan(column)]
                denom = max(1, int(column.size) - 1)
                scales.append(float(np.sqrt(np.sum(column ** 2) / denom)) if column.size else np.nan)
            scale_attr = np.asarray(scales, dtype=float)
            with np.errstate(divide="ignore", invalid="ignore"):
                data = data / scale_attr
    else:
        scale_attr = np.asarray(scale, dtype=float).ravel()
        if scale_attr.size != ncol:
            raise ValueError("length of 'scale' must equal the number of columns of 'x'")
        with np.errstate(divide="ignore", invalid="ignore"):
            data = data / scale_attr
    return np.array(data, order="F"), center_attr, scale_attr


def scale_zoo(x: Zoo, center: Any = True, scale: Any = True) -> Zoo:
    """Center and scale the core data, keeping the index."""
    scaled, center_attr, scale_attr = _scale_matrix(x.data, center=center, scale=scale)
    out = zoo(scaled, x.index, frequency=x.frequency)
    out.colnames = None if x.colnames is None else list(x.colnames)
    if center_attr is not None:
        out.extra["scaled:center"] = center_attr if center_attr.size > 1 else center_attr.reshape(())
    if scale_attr is not None:
        out.extra["scaled:scale"] = scale_attr if scale_attr.size > 1 else scale_attr.reshape(())
    return out


def mean_zoo(x: Zoo, trim: float = 0.0, na_rm: bool = False, **kwargs: Any) -> float:
    """Mean of the core data."""
    del kwargs
    values = _as_float_array(x.data).ravel(order="F")
    if na_rm:
        values = values[~np.isnan(values)]
    elif np.any(np.isnan(values)):
        return float("nan")
    if values.size == 0:
        return float("nan")
    if trim:
        if trim < 0 or trim >= 0.5:
            raise ValueError("trim must be in [0, 0.5)")
        ordered = np.sort(values)
        k = int(math.floor(trim * ordered.size))
        if k:
            ordered = ordered[k:-k] if k < ordered.size else ordered[:0]
        if ordered.size == 0:
            return float("nan")
        return float(np.mean(ordered))
    return float(np.sum(values) / values.size)


def xtfrm_zoo(x: Zoo) -> np.ndarray:
    """Core data, the order key of a zoo series."""
    return np.array(x.data, copy=True)


def rev_zoo(x: Zoo) -> Zoo:
    """Reverse the observations in time. The index stays sorted."""
    positions = _order_positions(time(x))
    reversed_positions = positions[::-1]
    idx = np.asarray(time(x))[reversed_positions]
    data = x.data
    if data.ndim == 1:
        new = np.array(data, copy=True)
    else:
        new = np.array(data, order="F", copy=True)
    out = zoo(new, idx, frequency=x.frequency)
    out.colnames = None if x.colnames is None else list(x.colnames)
    out.logical = bool(x.logical)
    return out


def _median_values(values: np.ndarray, na_rm: bool = False) -> float:
    data = _as_float_array(values).ravel(order="F")
    if na_rm:
        data = data[~np.isnan(data)]
    elif np.any(np.isnan(data)):
        return float("nan")
    n = int(data.size)
    if n == 0:
        return float("nan")
    half = (n + 1) // 2
    ordered = np.sort(data)
    if n % 2 == 1:
        return float(ordered[half - 1])
    return float(np.mean(ordered[half - 1:half + 1]))


def median_zoo(x: Zoo, na_rm: bool = False, **kwargs: Any) -> float:
    """Median of the core data. Missing values stay missing unless ``na_rm``."""
    del kwargs
    return _median_values(x.data, na_rm=na_rm)


def _formatc_fg(value: float, digits: int = 7) -> str:
    if math.isnan(value):
        return ""
    if value == 0:
        return "0"
    return format(float(value), f".{int(digits)}g")


def _format_perc(probs: np.ndarray, digits: int = 7) -> list[str]:
    labels = []
    for prob in np.asarray(probs, dtype=float):
        if math.isnan(prob):
            labels.append("")
        else:
            labels.append(_formatc_fg(100.0 * float(prob), digits=digits) + "%")
    return labels


def _quantile_values(x: np.ndarray, probs: np.ndarray, type: int = 7, fuzz: float | None = None) -> np.ndarray:
    data = np.sort(np.asarray(x, dtype=float).ravel())
    probs = np.asarray(probs, dtype=float)
    if fuzz is None:
        fuzz = 0.0 if int(type) == 7 else 4 * _EPS
    n = int(data.size)

    def floor_f(np_value: np.ndarray) -> np.ndarray:
        return np.floor(np.asarray(np_value, dtype=float) * (1.0 + fuzz))

    if int(type) == 7:
        index_value = 1.0 + max(n - 1, 0) * probs
        lo = floor_f(index_value)
        hi = np.ceil(index_value)
        qs = _take(data, lo)
        hi_vals = _take(data, hi)
        p_ok = ~np.isnan(probs)
        select = np.zeros(probs.shape, dtype=bool)
        for i in range(probs.size):
            if not p_ok[i]:
                select[i] = True
                continue
            if index_value[i] > lo[i] and not (math.isnan(hi_vals[i]) or math.isnan(qs[i])) and hi_vals[i] != qs[i]:
                select[i] = True
        h = (index_value - lo)[select]
        qs = qs.copy()
        qs[select] = (1.0 - h) * qs[select] + h * hi_vals[select]
        qs[~p_ok] = probs[~p_ok]
        return qs
    p_ok = ~np.isnan(probs)
    if type <= 3:
        nppm = n * probs - 0.5 if type == 3 else n * probs
        j = floor_f(nppm)
        if type == 1:
            h = np.logical_or(~p_ok, nppm > j).astype(float)
        elif type == 2:
            h = ((nppm > j).astype(float) + 1.0) / 2.0
        else:
            h = np.logical_or(np.logical_or(~p_ok, nppm != j), (j.astype(int) % 2) == 1).astype(float)
    else:
        a_b = {4: (0.0, 1.0), 5: (0.5, 0.5), 6: (0.0, 0.0), 7: (1.0, 1.0), 8: (1.0 / 3.0, 1.0 / 3.0), 9: (3.0 / 8.0, 3.0 / 8.0)}
        a, b = a_b[int(type)]
        nppm = a + probs * (n + 1 - a - b)
        j = floor_f(nppm)
        h = nppm - j
        small = np.abs(h) < fuzz
        h = h.copy()
        h[small] = 0.0
    if n == 0:
        extended = np.array([np.nan, np.nan, np.nan, np.nan])
    else:
        extended = np.concatenate([data[:1], data[:1], data, data[-1:], data[-1:]])
    qs = _take(extended, j + 2)
    hi = _take(extended, j + 3)
    replace = (~np.isnan(h)) & (h == 1)
    qs = qs.copy()
    qs[replace] = hi[replace]
    other = (0 < h) & (h < 1) & (qs != hi)
    other = np.where(np.isnan(other), True, other).astype(bool)
    if np.any(other):
        qs[other] = ((1.0 - h) * _take(extended, j + 2) + h * hi)[other]
    qs[~p_ok] = probs[~p_ok]
    return qs


def _take(data: np.ndarray, idx: np.ndarray) -> np.ndarray:
    idx = np.asarray(idx, dtype=float)
    out = np.full(idx.shape, np.nan, dtype=float)
    if data.size == 0:
        return out
    ok = np.isfinite(idx) & (idx >= 1) & (idx <= data.size)
    out[ok] = data[idx[ok].astype(int) - 1]
    return out


class NumericVector:
    """A numeric result that may carry R-style names, such as quantile labels."""

    def __init__(self, data: Any, names: list[str] | None = None) -> None:
        self.data = np.asarray(data, dtype=float)
        self.names = names

    def __array__(self, dtype: Any = None) -> np.ndarray:
        return np.asarray(self.data, dtype=dtype)

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return int(self.data.size)


def quantile_zoo(
    x: Zoo,
    probs: Any = None,
    na_rm: bool = False,
    names: bool = True,
    type: int = 7,
    digits: int = 7,
    **kwargs: Any,
) -> NumericVector:
    """Sample quantiles of the core data. The default is R's type 7."""
    del kwargs
    if probs is None:
        probs_array = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    else:
        probs_array = np.atleast_1d(np.asarray(probs, dtype=float))
    type_value = int(type)
    if type_value < 1 or type_value > 9:
        raise ValueError("'type' must be an integer in 1..9")
    data = _as_float_array(x.data).ravel(order="F")
    if na_rm:
        data = data[~np.isnan(data)]
    elif np.any(np.isnan(data)):
        raise ValueError("missing values and NaN's not allowed if 'na.rm' is FALSE")
    eps = 100 * _EPS
    p_ok = ~np.isnan(probs_array)
    if np.any(p_ok & ((probs_array < -eps) | (probs_array > 1 + eps))):
        raise ValueError("'probs' outside [0,1]")
    clipped = np.clip(np.where(np.isnan(probs_array), np.nan, probs_array), 0, 1)
    # np.clip turns NaN into NaN. Keep that.
    clipped = probs_array.copy()
    finite = np.isfinite(probs_array)
    clipped[finite] = np.minimum(1.0, np.maximum(0.0, probs_array[finite]))
    fuzz = 0.0 if type_value == 7 else 4 * _EPS
    values = _quantile_values(data, clipped, type=type_value, fuzz=fuzz)
    labels = _format_perc(clipped, digits=digits) if names and probs_array.size else None
    return NumericVector(values, labels)


def _align(series: list[Zoo], how: str) -> list[Zoo]:
    """Align series on the union (``all=TRUE``) or the intersection (``all=FALSE``)."""
    if not series:
        return []
    indexes = [np.asarray(item.index) for item in series]
    for item in indexes:
        if len(set(_match_self(item).tolist())) < item.size:
            raise ValueError("series cannot be merged with non-unique index entries in a series")
    combined = np.concatenate([np.asarray(item, dtype=float) for item in indexes]) if indexes else np.array([])
    # count occurrences of each key across series (one count per series that contains it)
    from collections import Counter
    counts: Counter[tuple] = Counter()
    ordered_keys: list[tuple] = []
    seen = set()
    for item in indexes:
        local = set()
        for value in np.asarray(item, dtype=float):
            key = _key(value)
            if key in local:
                continue
            local.add(key)
            counts[key] += 1
            if key not in seen:
                seen.add(key)
                ordered_keys.append(key)
    if how == "intersection":
        chosen = [key for key in ordered_keys if counts[key] == len(series)]
    else:
        chosen = ordered_keys
    chosen_values = []
    for key in chosen:
        if key[0] == "na":
            chosen_values.append(np.nan)
        else:
            chosen_values.append(key[1])
    if chosen_values:
        order = _order_positions(chosen_values)
        new_index = np.asarray(chosen_values, dtype=float)[order]
    else:
        new_index = np.array([], dtype=float)
    aligned = []
    for item in series:
        mapping = {_key(value): position for position, value in enumerate(np.asarray(item.index, dtype=float))}
        if item.data.ndim == 1:
            out = np.full(new_index.shape, np.nan, dtype=float)
            for j, value in enumerate(new_index):
                key = _key(value)
                if key in mapping:
                    out[j] = _as_float_array(item.data).ravel()[mapping[key]]
        else:
            out = np.full((new_index.size, item.data.shape[1]), np.nan, dtype=float, order="F")
            data = _as_float_array(item.data)
            for j, value in enumerate(new_index):
                key = _key(value)
                if key in mapping:
                    out[j, :] = data[mapping[key], :]
        rebuilt = zoo(out, new_index, frequency=item.frequency)
        rebuilt.logical = item.logical
        rebuilt.colnames = None if item.colnames is None else list(item.colnames)
        aligned.append(rebuilt)
    del combined
    return aligned


def _recycle(values: Any, length: int) -> np.ndarray:
    array = _as_float_array(values).ravel(order="F")
    if length == 0:
        return np.array([], dtype=float)
    if array.size == 0:
        raise ValueError("replacement has length zero")
    if length % array.size != 0:
        warnings.warn("longer object length is not a multiple of shorter object length", stacklevel=3)
    return np.resize(array, length)


def ifelse_zoo(test: Any, yes: Any, no: Any) -> Zoo:
    """Elementwise choice. Zoo arguments are aligned on the union of their indexes."""
    if not is_zoo(test):
        if not is_zoo(yes):
            raise ValueError("test is not a zoo object and yes has no index")
        test = zoo(_as_float_array(test), index(yes), frequency=getattr(yes, "frequency", None))
    zoos = [item for item in (test, yes, no) if is_zoo(item)]
    aligned = {id(item): item for item in zoos}
    if len(zoos) >= 1:
        merged = _align(zoos, "union")
        for original, new in zip(zoos, merged):
            aligned[id(original)] = new
    test_series = aligned[id(test)]
    test_values = _as_float_array(test_series.data).ravel(order="F")
    logical = np.full(test_values.shape, np.nan)
    present = ~np.isnan(test_values)
    logical[present] = (test_values[present] != 0).astype(float)
    n = int(logical.size)

    def take(value: Any) -> np.ndarray:
        if is_zoo(value):
            return _as_float_array(aligned[id(value)].data).ravel(order="F")
        return _recycle(value, n)

    yes_values = take(yes)
    no_values = take(no)
    if yes_values.size != n:
        yes_values = _recycle(yes_values, n)
    if no_values.size != n:
        no_values = _recycle(no_values, n)
    out = np.full(n, np.nan, dtype=float)
    true = logical == 1
    false = logical == 0
    out[true] = yes_values[true]
    out[false] = no_values[false]
    result = zoo(out, test_series.index, frequency=test_series.frequency)
    return result


def _apply_op(op: Any, left: np.ndarray, right: np.ndarray | None = None) -> tuple[np.ndarray, bool]:
    if right is None:
        with np.errstate(divide="ignore", invalid="ignore"):
            values = op(left)
        return np.asarray(values, dtype=float), False
    if op in (operator.gt, operator.ge, operator.lt, operator.le, operator.eq, operator.ne):
        broadcast_left, broadcast_right = np.broadcast_arrays(left, right)
        out = np.full(broadcast_left.shape, np.nan, dtype=float)
        mask = ~(np.isnan(broadcast_left) | np.isnan(broadcast_right))
        out[mask] = op(broadcast_left[mask], broadcast_right[mask]).astype(float)
        return out, True
    with np.errstate(divide="ignore", invalid="ignore"):
        values = op(left, right)
    return np.asarray(values, dtype=float), False


def _ops(e1: Any, e2: Any = None, op: Any = operator.add, unary: bool = False) -> Zoo:
    if unary or e2 is None:
        if not is_zoo(e1):
            raise ValueError("Ops.zoo is for zoo objects")
        values, logical = _apply_op(op, _as_float_array(e1.data))
        out = zoo(values.reshape(e1.data.shape, order="F") if e1.data.ndim == 2 else values.ravel(), e1.index, frequency=e1.frequency)
        out.logical = logical
        out.colnames = None if e1.colnames is None else list(e1.colnames)
        return out
    if is_zoo(e1) and is_zoo(e2):
        left, right = _align([e1, e2], "intersection")
        left_data = _as_float_array(left.data)
        right_data = _as_float_array(right.data)
        values, logical = _apply_op(op, left_data, right_data)
        shaped = values.reshape(left.data.shape, order="F") if left.data.ndim == 2 else values.ravel()
        out = zoo(shaped, left.index, frequency=left.frequency)
        out.logical = logical
        out.colnames = None if left.colnames is None else list(left.colnames)
        return out
    if is_zoo(e1):
        values, logical = _apply_op(op, _as_float_array(e1.data), _as_float_array(e2))
        shaped = values.reshape(e1.data.shape, order="F") if values.shape == e1.data.shape else values.ravel()
        out = zoo(shaped, e1.index, frequency=e1.frequency)
        out.logical = logical or e1.logical and op in (operator.neg,)
        out.colnames = None if e1.colnames is None else list(e1.colnames)
        return out
    if is_zoo(e2):
        values, logical = _apply_op(op, _as_float_array(e1), _as_float_array(e2.data))
        shaped = values.reshape(e2.data.shape, order="F") if values.shape == e2.data.shape else values.ravel()
        out = zoo(shaped, e2.index, frequency=e2.frequency)
        out.logical = logical
        out.colnames = None if e2.colnames is None else list(e2.colnames)
        return out
    values, _logical = _apply_op(op, _as_float_array(e1), _as_float_array(e2))
    raise ValueError("Ops.zoo is for zoo objects")


def Ops_zoo(e1: Any, e2: Any = None, op: Any = operator.add) -> Zoo:
    """Group generic for arithmetic and comparison. Two series intersect first."""
    if e2 is None:
        return _ops(e1, None, op, unary=True)
    return _ops(e1, e2, op, unary=False)


def _cum(x: Zoo, fn) -> Zoo:
    data = _as_float_array(x.data)
    if data.ndim == 1:
        new = fn(data)
    else:
        new = np.array(np.apply_along_axis(fn, 0, data), order="F")
    out = zoo(new, x.index, frequency=x.frequency)
    out.colnames = None if x.colnames is None else list(x.colnames)
    return out


def cumsum_zoo(x: Zoo) -> Zoo:
    return _cum(x, np.cumsum)


def cumprod_zoo(x: Zoo) -> Zoo:
    return _cum(x, np.cumprod)


def cummin_zoo(x: Zoo) -> Zoo:
    return _cum(x, np.minimum.accumulate)


def cummax_zoo(x: Zoo) -> Zoo:
    return _cum(x, np.maximum.accumulate)


def t_zoo(x: Zoo) -> np.ndarray:
    """Transpose. A vector becomes a one-row matrix. The result is not a zoo series."""
    data = _as_float_array(x.data)
    if data.ndim == 1:
        data = np.array(data.reshape(1, -1), order="F")
        return data
    return np.array(data.T, order="F", copy=True)


def split_zoo(x: Zoo, f: Any, drop: bool = False, **kwargs: Any) -> dict[str, Zoo]:
    """Split a series by a grouping vector. Names follow sorted levels."""
    del kwargs
    groups = np.asarray(f)
    if groups.ndim > 1:
        groups = groups.ravel(order="F")
    if groups.size != _nrow(x):
        raise ValueError("'f' must have the same length as the series")
    levels = []
    seen = set()
    for value in groups:
        if _is_na(value):
            continue
        key = str(int(value)) if isinstance(value, (int, np.integer)) or (isinstance(value, float) and float(value).is_integer()) else str(value)
        if key not in seen:
            seen.add(key)
            levels.append(key)
    levels = sorted(levels)
    result: dict[str, Zoo] = {}
    for level in levels:
        positions = []
        for i, value in enumerate(groups):
            if _is_na(value):
                continue
            key = str(int(value)) if isinstance(value, (int, np.integer)) or (isinstance(value, float) and float(value).is_integer()) else str(value)
            if key == level:
                positions.append(i)
        if not positions and drop:
            continue
        result[level] = _subset_rows(x, positions, drop=drop if _is_matrix(x) else True)
    return result


def r_sum(x: Any, na_rm: bool = False, **kwargs: Any) -> float:
    """R's ``sum``. An empty sum is 0. Missing values stay missing unless ``na_rm``."""
    del kwargs
    values = _as_float_array(x).ravel(order="F")
    if na_rm:
        values = values[~np.isnan(values)]
    elif np.any(np.isnan(values)):
        return float("nan")
    if values.size == 0:
        return 0.0
    return float(np.sum(values))


def _aggregate_rows(data: np.ndarray, codes: np.ndarray, fun, kwargs: dict) -> tuple[np.ndarray, list[float]]:
    """Aggregate rows by 1-based group codes, in sorted code order."""
    valid = np.array([not math.isnan(code) for code in codes])
    used = codes[valid]
    if data.ndim == 1:
        used_data = data[valid]
    else:
        used_data = data[valid, :]
    unique_codes = sorted(set(float(code) for code in used))
    rows = []
    for code in unique_codes:
        mask = used == code
        if used_data.ndim == 1:
            rows.append(fun(used_data[mask], **kwargs))
        else:
            rows.append([fun(used_data[mask, j], **kwargs) for j in range(used_data.shape[1])])
    if not rows:
        empty = np.array([], dtype=float) if data.ndim == 1 else np.zeros((0, data.shape[1]), dtype=float)
        return empty, []
    if data.ndim == 1:
        return np.asarray(rows, dtype=float), unique_codes
    return np.array(rows, dtype=float, order="F"), unique_codes


def _as_by_vector(by: Any, idx: np.ndarray) -> np.ndarray:
    if callable(by):
        by = by(idx)
    if isinstance(by, (list, tuple)) and by and isinstance(by[0], (list, tuple, np.ndarray)) and not np.isscalar(by[0]):
        by = by[0]
    return np.asarray(by)


def aggregate_zoo(
    x: Zoo,
    by: Any,
    fun=None,
    regular: bool | None = None,
    frequency: float | None = None,
    coredata: bool = True,
    **kwargs: Any,
) -> Zoo:
    """Aggregate a series along a coarser index. The default summary is the sum."""
    if fun is None:
        fun = r_sum
    if frequency is None:
        if regular is None:
            regular = bool(x.regular)
    else:
        if regular is False:
            warnings.warn("‘regular’ is ignored", stacklevel=2)
        regular = True
    idx = np.asarray(x.index)
    by_vector = _as_by_vector(by, idx)
    if np.asarray(by_vector).size != idx.size:
        raise ValueError("length(time(x)) == length(by[[1]]) is not TRUE")
    codes = _match_self(by_vector)
    if not coredata:
        # FUN receives each group's series, column by column.
        return _aggregate_zoo_objects(x, by_vector, codes, fun, kwargs, regular, frequency)
    data = _as_float_array(x.data)
    if x.data.ndim == 2:
        data = data.reshape(x.data.shape, order="F")
    values, _codes = _aggregate_rows(data if data.ndim == 1 else np.array(data, order="F"), codes, fun, kwargs)
    if x.data.ndim == 2 and values.ndim == 1 and x.data.shape[1] == 1:
        values = values.reshape(-1, 1)
    if x.data.ndim == 2:
        if x.colnames is not None:
            colnames = list(x.colnames)
        else:
            colnames = [f"V{j + 1}" for j in range(x.data.shape[1])]
    else:
        colnames = None
    ix = _my_unique(by_vector)
    finite = np.array([not _is_na(value) for value in ix])
    ix_clean = ix[finite] if ix.size else ix
    out = zoo(values, ix_clean)
    out.colnames = colnames
    if regular:
        freq = frequency_of(out) if frequency is None else float(frequency)
        out = zoo(values, ix, frequency=freq)
        out.colnames = colnames
    return out


def _one_column(x: Zoo, column: int) -> Zoo:
    data = _as_float_array(x.data)[:, column]
    out = zoo(data, x.index, frequency=x.frequency)
    return out


def _aggregate_zoo_objects(x, by_vector, codes, fun, kwargs, regular, frequency) -> Zoo:
    valid_codes = []
    groups = []
    for code in sorted(set(float(item) for item in codes if not math.isnan(item))):
        positions = [i for i, value in enumerate(codes) if value == code]
        if x.data.ndim == 1:
            groups.append(fun(_subset_rows(x, positions), **kwargs))
        else:
            groups.append([fun(_subset_rows(_one_column(x, j), positions), **kwargs) for j in range(x.data.shape[1])])
        valid_codes.append(code)
    if x.data.ndim == 1:
        values = np.asarray(groups, dtype=float)
        colnames = None
    else:
        values = np.array(groups, dtype=float, order="F")
        colnames = list(x.colnames) if x.colnames is not None else [f"V{j + 1}" for j in range(x.data.shape[1])]
    ix = _my_unique(by_vector)
    finite = np.array([not _is_na(value) for value in ix])
    ix_clean = ix[finite] if ix.size else ix
    out = zoo(values, ix_clean)
    out.colnames = colnames
    if regular:
        freq = frequency_of(out) if frequency is None else float(frequency)
        out = zoo(values, ix, frequency=freq)
        out.colnames = colnames
    return out


def r_print(x: Any) -> None:
    """Print the way the R example prints this object."""
    if is_zoo(x):
        sys.stdout.write(_format_zoo(x) + "\n")
        return
    if isinstance(x, (bool, np.bool_)):
        sys.stdout.write("[1] TRUE\n" if bool(x) else "[1] FALSE\n")
        return
    if isinstance(x, NumericVector):
        if x.names:
            sys.stdout.write(_format_named(list(x.names), r_format_numeric(x.data)) + "\n")
        else:
            sys.stdout.write(_format_atomic(x.data) + "\n")
        return
    if isinstance(x, dict) and x and all(isinstance(value, list) for value in x.values()):
        sys.stdout.write(_format_summary(x) + "\n")
        return
    array = np.asarray(x)
    logical = getattr(x, "logical", False)
    sys.stdout.write(_format_atomic(array, logical=logical) + "\n")


def _bind(name: str, op: Any, unary: bool = False, reflected: bool = False):
    def method(self, other=None):
        if unary:
            return _ops(self, None, op, unary=True)
        if reflected:
            return _ops(other, self, op)
        return _ops(self, other, op)

    method.__name__ = name
    return method


Zoo.__add__ = _bind("__add__", operator.add)
Zoo.__radd__ = _bind("__radd__", operator.add, reflected=True)
Zoo.__sub__ = _bind("__sub__", operator.sub)
Zoo.__rsub__ = _bind("__rsub__", operator.sub, reflected=True)
Zoo.__mul__ = _bind("__mul__", operator.mul)
Zoo.__rmul__ = _bind("__rmul__", operator.mul, reflected=True)
Zoo.__truediv__ = _bind("__truediv__", operator.truediv)
Zoo.__rtruediv__ = _bind("__rtruediv__", operator.truediv, reflected=True)
Zoo.__pow__ = _bind("__pow__", operator.pow)
Zoo.__rpow__ = _bind("__rpow__", operator.pow, reflected=True)
Zoo.__floordiv__ = _bind("__floordiv__", operator.floordiv)
Zoo.__rfloordiv__ = _bind("__rfloordiv__", operator.floordiv, reflected=True)
Zoo.__mod__ = _bind("__mod__", operator.mod)
Zoo.__rmod__ = _bind("__rmod__", operator.mod, reflected=True)
Zoo.__neg__ = _bind("__neg__", operator.neg, unary=True)
Zoo.__pos__ = _bind("__pos__", operator.pos, unary=True)
Zoo.__gt__ = _bind("__gt__", operator.gt)
Zoo.__ge__ = _bind("__ge__", operator.ge)
Zoo.__lt__ = _bind("__lt__", operator.lt)
Zoo.__le__ = _bind("__le__", operator.le)
Zoo.__eq__ = _bind("__eq__", operator.eq)
Zoo.__ne__ = _bind("__ne__", operator.ne)
Zoo.__str__ = lambda self: _format_zoo(self)
Zoo.__repr__ = lambda self: _format_zoo(self)
