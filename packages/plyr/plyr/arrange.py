"""Reorder a data frame the way plyr 1.8.9 ``arrange`` does.

``arrange`` evaluates ``order`` on the columns and returns those rows.
Row names are cleared. ``desc`` is ``-xtfrm``, which is what the examples
pass into ``order``. Numeric, logical, and factor keys use a stable sort,
the same order as R's radix method. Character keys use the ICU collator.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import math
import os
from datetime import date, datetime

import numpy as np


_ORDER_ARGUMENTS = {"na.last", "na_last", "decreasing", "method"}
_METHODS = ("auto", "shell", "radix")


class Factor:
    """Factor stored as labels. ``None`` is a missing value."""

    def __init__(self, values, levels, ordered=False):
        self.levels = [None if level is None else str(level) for level in levels]
        self.values = [_factor_value(value) for value in values]
        self.ordered = bool(ordered)

    def __len__(self):
        return len(self.values)


def _factor_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value)


class Desc:
    """A column that ``order`` should see through ``desc``."""

    def __init__(self, value):
        self.value = value


class DataFrame:
    """Column-oriented frame. Column order is insertion order."""

    def __init__(self, columns=None, row_names=None):
        self.columns = {}
        if columns:
            for name, values in columns.items():
                self.columns["" if name is None else str(name)] = values
        lengths = [_length(column) for column in self.columns.values()]
        if len(set(lengths)) > 1:
            raise ValueError("columns must have one common length")
        self.nrows = lengths[0] if lengths else 0
        self.row_names = None if row_names is None else [str(name) for name in row_names]

    def __len__(self):
        return self.nrows

    def __str__(self):
        return format_frame(self)


def desc(x):
    """``-xtfrm(x)``, so ``arrange`` sorts this key downwards.

    A string is a column name. ``arrange`` looks it up. Anything else is
    transformed immediately, which is what ``order(desc(x))`` evaluates.
    """
    if isinstance(x, str):
        return Desc(x)
    return _negate_xtfrm(x)


def arrange(df, *dots, **kwargs):
    """Reorder ``df`` by the columns or vectors in ``dots``.

    ``df`` is a :class:`DataFrame` or a dict of columns. A string selects
    a column. ``desc`` negates ``xtfrm`` of that column before ``order``.
    A bare sequence is an ordering vector. ``na.last``, ``decreasing``, and
    ``method`` are forwarded to ``order``. The result has no row names.
    """
    unexpected = [name for name in kwargs if name not in _ORDER_ARGUMENTS]
    if unexpected:
        name = unexpected[0]
        raise TypeError(f"unused argument ({name})")
    frame = _as_frame(df)
    keys = [_resolve_key(spec, frame) for spec in dots]
    permutation = order(*keys, **kwargs)
    if len(permutation) != len(frame):
        raise ValueError("Length of ordering vectors don't match data frame size")
    positions = [index - 1 for index in permutation]
    columns = {name: _take(column, positions) for name, column in frame.columns.items()}
    return DataFrame(columns)


def order(*columns, **kwargs):
    """1-based ``order``. ``na.last`` defaults to true and ``method`` to auto."""
    na_last = kwargs.get("na.last", kwargs.get("na_last", True))
    decreasing = kwargs.get("decreasing", False)
    method = _match_method(kwargs.get("method", "auto"))
    if not columns:
        return []
    prepared = [_order_column(column) for column in columns]
    lengths = [_length(column) for column in prepared]
    if len(set(lengths)) > 1:
        raise ValueError("argument lengths differ")
    if lengths[0] == 0:
        return []
    use_radix = method == "radix" or (method == "auto" and _all_radix(prepared))
    if not use_radix and _decreasing_length(decreasing) > 1:
        raise ValueError('\'decreasing\' of length > 1 is only for method = "radix"')
    flags = _decreasing_flags(decreasing, len(prepared))
    na_mode = _na_mode(na_last)
    if use_radix or _all_radix(prepared):
        positions = _radix_permutation(prepared, flags, na_mode)
    else:
        positions = _shell_permutation(prepared, flags, na_mode)
    return [index + 1 for index in positions]


def format_frame(frame):
    """Print a frame the way R prints a data frame."""
    frame = frame if isinstance(frame, DataFrame) else _as_frame(frame)
    names = list(frame.columns)
    nrow = len(frame)
    if not names:
        noun = "row" if nrow == 1 else "rows"
        return f"data frame with 0 columns and {nrow} {noun}"
    if nrow == 0:
        shown = " ".join(names)
        return f"[1] {shown}\n<0 rows> (or 0-length row.names)"
    labels = frame.row_names if frame.row_names is not None else [str(index) for index in range(1, nrow + 1)]
    cells = [_column_cells(frame.columns[name]) for name in names]
    widths = [
        max([len(name), *(len(cell) for cell in column)])
        for name, column in zip(names, cells)
    ]
    row_width = max(len(label) for label in labels)
    header = " ".join(name.rjust(width) for name, width in zip(names, widths))
    lines = [" " * row_width + " " + header]
    for index, label in enumerate(labels):
        body = " ".join(column[index].rjust(width) for column, width in zip(cells, widths))
        lines.append(label.ljust(row_width) + " " + body)
    return "\n".join(lines)


def _as_frame(df):
    if isinstance(df, DataFrame):
        return df
    if isinstance(df, dict):
        return DataFrame(df)
    raise ValueError("is.data.frame(df) is not TRUE ")


def _length(column):
    if isinstance(column, Factor):
        return len(column)
    if isinstance(column, np.ndarray):
        if column.ndim == 0:
            return 1
        return int(column.shape[0])
    if isinstance(column, str):
        raise TypeError("a character column must be a list of strings, not one string")
    return len(column)


def _resolve_key(spec, frame):
    if isinstance(spec, Desc):
        return _negate_xtfrm(_lookup(spec.value, frame))
    return _lookup(spec, frame)


def _lookup(spec, frame):
    if isinstance(spec, str):
        if spec not in frame.columns:
            raise ValueError(f"object '{spec}' not found")
        return frame.columns[spec]
    if isinstance(spec, Factor):
        return spec
    if isinstance(spec, np.ndarray):
        if spec.ndim == 0:
            return [spec.item()]
        return spec
    if isinstance(spec, (list, tuple)):
        return list(spec)
    if isinstance(spec, (int, float, bool)) and not isinstance(spec, bool):
        return [spec]
    if isinstance(spec, bool):
        return [spec]
    raise ValueError(f"object '{spec}' not found")


def _order_column(column):
    """The vector ``order`` compares. Objects pass through ``xtfrm``."""
    if isinstance(column, Factor):
        return _factor_codes(column)
    if isinstance(column, np.ndarray):
        if column.dtype == object or column.dtype.kind in "SU":
            return [_python_value(value) for value in column.tolist()]
        if column.dtype.kind == "b":
            return [bool(value) for value in column.tolist()]
        return column
    if isinstance(column, datetime):
        return [column.timestamp()]
    if isinstance(column, date):
        return [float(column.toordinal() - date(1970, 1, 1).toordinal())]
    return column


def _python_value(value):
    if value is None:
        return None
    if isinstance(value, np.generic):
        if isinstance(value, np.floating) and math.isnan(float(value)):
            return float("nan")
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        return str(value)
    return value


def _factor_codes(column):
    positions = {level: index for index, level in enumerate(column.levels, start=1)}
    codes = []
    for value in column.values:
        if value is None:
            codes.append(None)
        else:
            codes.append(positions.get(value))
    return codes


def _xtfrm(column):
    column = _order_column(column)
    if isinstance(column, np.ndarray):
        column = [_python_value(value) for value in column.tolist()]
    if not column:
        return []
    sample = next((value for value in column if not _is_missing(value)), None)
    if sample is None or _is_number(sample):
        return [_number_or_missing(value) for value in column]
    if isinstance(sample, str):
        return _rank_min(column)
    return [_number_or_missing(value) for value in column]


def _number_or_missing(value):
    if _is_missing(value):
        return None if value is None or not _is_nan(value) else float("nan")
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def _negate_xtfrm(column):
    negated = []
    for value in _xtfrm(column):
        if value is None:
            negated.append(None)
            continue
        number = float(value)
        if math.isnan(number):
            negated.append(float("nan"))
        elif number == 0.0:
            negated.append(0.0)
        else:
            negated.append(-number)
    return negated


def _rank_min(values):
    present = [(index, value) for index, value in enumerate(values) if isinstance(value, str)]
    present.sort(key=lambda item: _Text(item[1], False))
    ranks = [None if not isinstance(value, str) else 0 for value in values]
    previous = None
    rank = 0
    for position, (index, value) in enumerate(present, start=1):
        if previous is None or _collator().compare(previous, value) != 0:
            rank = position
            previous = value
        ranks[index] = float(rank)
    return ranks


def _all_radix(columns):
    for column in columns:
        if _length(column) > 2**31 - 1:
            return False
        if not _is_radix_column(column):
            return False
    return True


def _is_radix_column(column):
    if isinstance(column, np.ndarray):
        return column.dtype.kind in "biufc" or column.dtype == object and _object_array_is_numeric(column)
    for value in column:
        if _is_missing(value) or _is_number(value):
            continue
        return False
    return True


def _object_array_is_numeric(column):
    for value in column.tolist():
        if _is_missing(value) or _is_number(value):
            continue
        return False
    return True


def _is_number(value):
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return True
    return False


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, (float, np.floating)):
        return bool(math.isnan(float(value)))
    return False


def _is_nan(value):
    return isinstance(value, (float, np.floating)) and math.isnan(float(value))


def _decreasing_length(decreasing):
    if isinstance(decreasing, (bool, np.bool_)):
        return 1
    if isinstance(decreasing, np.ndarray):
        return int(decreasing.size)
    if isinstance(decreasing, (list, tuple)):
        return len(decreasing)
    return 1


def _decreasing_flags(decreasing, count):
    if isinstance(decreasing, (bool, np.bool_)):
        return [bool(decreasing)] * count
    if isinstance(decreasing, np.ndarray):
        flags = [bool(item) for item in decreasing.tolist()]
    elif isinstance(decreasing, (list, tuple)):
        flags = [bool(item) for item in decreasing]
    else:
        return [bool(decreasing)] * count
    if not flags:
        raise ValueError("argument lengths differ")
    if len(flags) == count:
        return flags
    return [flags[index % len(flags)] for index in range(count)]


def _na_mode(na_last):
    """``True`` keeps missing values last, ``False`` first, ``None`` drops them."""
    if na_last is None:
        return None
    if isinstance(na_last, float) and math.isnan(na_last):
        return None
    if isinstance(na_last, np.floating) and np.isnan(na_last):
        return None
    if bool(na_last):
        return True
    return False


def _match_method(method):
    if method is None:
        return "auto"
    text = str(method)
    matches = [choice for choice in _METHODS if choice.startswith(text)]
    if len(matches) != 1:
        quoted = ", ".join("“" + choice + "”" for choice in _METHODS)
        raise ValueError(f"'arg' should be one of {quoted}")
    return matches[0]


def _as_float_and_missing(column):
    if isinstance(column, np.ndarray) and column.dtype.kind in "biuf":
        values = np.array(column, dtype=np.float64, copy=True)
        missing = np.isnan(values)
        values[missing] = 0.0
        return values, missing
    n = _length(column)
    values = np.zeros(n, dtype=np.float64)
    missing = np.zeros(n, dtype=bool)
    for index, value in enumerate(column):
        if value is None:
            missing[index] = True
            continue
        if isinstance(value, (bool, np.bool_)):
            values[index] = 1.0 if value else 0.0
            continue
        number = float(value)
        if math.isnan(number):
            missing[index] = True
            continue
        values[index] = number
    return values, missing


def _radix_permutation(columns, flags, na_mode):
    n = _length(columns[0])
    prepared = [_as_float_and_missing(column) for column in columns]
    idx = np.arange(n, dtype=np.intp)
    if na_mode is None:
        keep = np.ones(n, dtype=bool)
        for _values, missing in prepared:
            keep &= ~missing
        idx = idx[keep]
    for key in range(len(prepared) - 1, -1, -1):
        values, missing = prepared[key]
        current = values[idx]
        if flags[key]:
            current = np.negative(current)
        idx = idx[np.argsort(current, kind="stable")]
        if na_mode is True:
            idx = idx[np.argsort(missing[idx].astype(np.int8), kind="stable")]
        elif na_mode is False:
            present = np.logical_not(missing[idx]).astype(np.int8)
            idx = idx[np.argsort(present, kind="stable")]
    return idx.tolist()


def _shell_permutation(columns, flags, na_mode):
    n = _length(columns[0])
    lists = [_as_list(column) for column in columns]
    indexes = list(range(n))
    if na_mode is None:
        indexes = [
            index
            for index in indexes
            if not any(_is_missing(column[index]) for column in lists)
        ]

    def key(index):
        parts = []
        for column, reverse in zip(lists, flags):
            value = column[index]
            missing = _is_missing(value)
            if na_mode is True:
                parts.append(1 if missing else 0)
            elif na_mode is False:
                parts.append(0 if missing else 1)
            if missing:
                parts.append((0, 0.0))
            elif isinstance(value, str):
                parts.append(_Text(value, reverse))
            else:
                number = 1.0 if value is True else 0.0 if value is False else float(value)
                if number == 0.0:
                    number = 0.0
                parts.append(_Num(number, reverse))
        return tuple(parts)

    indexes.sort(key=key)
    return indexes


def _as_list(column):
    if isinstance(column, np.ndarray):
        return [_python_value(value) for value in column.tolist()]
    return list(column)


class _Num:
    def __init__(self, value, reverse):
        self.value = value
        self.reverse = reverse

    def __eq__(self, other):
        return isinstance(other, _Num) and self.value == other.value and self.reverse == other.reverse

    def __lt__(self, other):
        if not isinstance(other, _Num):
            return NotImplemented
        if self.reverse:
            return self.value > other.value
        return self.value < other.value


class _Text:
    def __init__(self, value, reverse):
        self.value = value
        self.reverse = reverse

    def __eq__(self, other):
        return (
            isinstance(other, _Text)
            and self.reverse == other.reverse
            and _collator().compare(self.value, other.value) == 0
        )

    def __lt__(self, other):
        if not isinstance(other, _Text):
            return NotImplemented
        compared = _collator().compare(self.value, other.value)
        if self.reverse:
            return compared > 0
        return compared < 0


def _collation_locale():
    for variable in ("LC_ALL", "LC_COLLATE", "LANG"):
        value = os.environ.get(variable)
        if value and value.lower() not in {"c", "posix"}:
            return value.split(".")[0]
    return "en_US"


class _Collator:
    """ICU collator. R's character ``order`` calls this."""

    def __init__(self):
        path = ctypes.util.find_library("icui18n")
        if not path:
            path = "libicui18n.so.76"
        library = ctypes.CDLL(path)
        version = "76"
        stem = os.path.basename(path)
        if ".so." in stem:
            version = stem.rsplit(".so.", 1)[1].split(".")[0]
        opener = getattr(library, f"ucol_open_{version}")
        compare = getattr(library, f"ucol_strcollUTF8_{version}")
        opener.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
        opener.restype = ctypes.c_void_p
        compare.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int),
        ]
        compare.restype = ctypes.c_int
        status = ctypes.c_int(0)
        collator = opener(_collation_locale().encode(), ctypes.byref(status))
        if not collator or status.value > 0:
            raise OSError(f"ucol_open failed for {_collation_locale()}")
        self._compare = compare
        self._collator = collator

    def compare(self, left, right):
        status = ctypes.c_int(0)
        raw_left = left.encode()
        raw_right = right.encode()
        return self._compare(
            self._collator,
            raw_left,
            len(raw_left),
            raw_right,
            len(raw_right),
            ctypes.byref(status),
        )


_COLLATOR = None


def _collator():
    global _COLLATOR
    if _COLLATOR is None:
        _COLLATOR = _Collator()
    return _COLLATOR


def _take(column, positions):
    if isinstance(column, Factor):
        return Factor([column.values[index] for index in positions], column.levels, column.ordered)
    if isinstance(column, np.ndarray):
        return column[np.asarray(positions, dtype=np.intp)]
    return [column[index] for index in positions]


def _column_cells(column):
    if isinstance(column, Factor):
        return [_factor_cell(column, value) for value in column.values]
    if isinstance(column, np.ndarray):
        values = [_python_value(value) for value in column.tolist()]
        return _cells_for_values(values)
    return _cells_for_values(list(column))


def _factor_cell(column, value):
    if value is None:
        return "<NA>"
    return "<NA>" if value is None else str(value)


def _cells_for_values(values):
    if not values:
        return []
    sample = next((value for value in values if not _is_missing(value)), None)
    if isinstance(sample, str):
        return ["<NA>" if value is None else str(value) for value in values]
    if isinstance(sample, bool) or any(isinstance(value, bool) for value in values):
        return [_logical_cell(value) for value in values]
    return _numeric_cells(values)


def _logical_cell(value):
    if value is None or _is_nan(value):
        return "NA"
    return "TRUE" if value else "FALSE"


def _decimals(value, digits=7):
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


def _needs_sci(value):
    if value == 0 or not math.isfinite(value):
        return False
    exponent = math.floor(math.log10(abs(value)))
    return exponent >= 5 or exponent < -4


def _scientific(value):
    if value == 0:
        return "0e+00"
    sign = "-" if math.copysign(1.0, value) < 0 else ""
    exponent = math.floor(math.log10(abs(value)))
    mantissa = abs(value) / (10**exponent)
    text = format(mantissa, ".6g")
    if text.startswith("10"):
        mantissa = float(text) / 10
        exponent += 1
        text = format(mantissa, ".6g")
    return f"{sign}{text}e{exponent:+03d}"


def _numeric_cells(values):
    finite = []
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        number = float(value)
        if math.isfinite(number):
            finite.append(number)
    decs = [_decimals(value) for value in finite]
    scientific = any(item is None or _needs_sci(value) for item, value in zip(decs, finite))
    places = 0
    if not scientific and decs:
        places = max(item for item in decs if item is not None)
    cells = []
    for value in values:
        if value is None:
            cells.append("NA")
            continue
        if isinstance(value, bool):
            cells.append("1" if value else "0")
            continue
        number = float(value)
        if math.isnan(number):
            cells.append("NaN")
        elif math.isinf(number):
            cells.append("Inf" if number > 0 else "-Inf")
        elif scientific:
            cells.append(_scientific(number))
        elif places == 0:
            cells.append(str(int(round(number))))
        else:
            cells.append(f"{number:.{places}f}")
    return cells
