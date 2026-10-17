"""Row-bind data frames the way plyr 1.8.9 ``rbind.fill`` does.

Missing columns are filled with NA. Column order is the order in which
names are first seen. A list of frames may be passed as the first
argument. ``NULL`` inputs are dropped. NumPy arrays with two or more
dimensions are array columns; a one-dimensional array is a vector.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone

import numpy as np


_EPOCH = date(1970, 1, 1).toordinal()


class Factor:
    """Factor stored as 1-based codes. ``None`` is a missing value.

    A level may itself be ``None``. That is an NA level, and a code that
    points at it is not a missing value.
    """

    def __init__(self, codes, levels, ordered=False, attributes=None):
        self.codes = [None if code is None else int(code) for code in codes]
        self.levels = list(levels)
        self.ordered = bool(ordered)
        self.attributes = dict(attributes or {})

    def __len__(self):
        return len(self.codes)


class Posixct:
    """Instants as seconds since the Unix epoch, with an R ``tzone``."""

    def __init__(self, seconds, tzone=None, attributes=None):
        self.seconds = list(seconds)
        self.tzone = tzone
        self.attributes = dict(attributes or {})

    def __len__(self):
        return len(self.seconds)


class Matrix:
    """Array column. The first axis is the row count, as in R."""

    def __init__(self, data, dimnames=None, dimnames_names=None, attributes=None):
        self.data = np.asarray(data)
        self.dimnames = None if dimnames is None else [None if item is None else list(item) for item in dimnames]
        self.dimnames_names = None if dimnames_names is None else list(dimnames_names)
        self.attributes = dict(attributes or {})

    def __len__(self):
        return int(self.data.shape[0]) if self.data.ndim else 1


class DataFrame:
    """Column-oriented frame. Column order is insertion order."""

    def __init__(self, columns=None, nrows=None, row_names=None):
        self.columns = {}
        self.attrs = {}
        if columns:
            for name, values in columns.items():
                self.columns["" if name is None else str(name)] = values
        lengths = [_nrow(column) for column in self.columns.values()]
        if lengths:
            if len(set(lengths)) != 1:
                raise ValueError("columns must have one common length")
            self.nrows = lengths[0]
        else:
            self.nrows = 0 if nrows is None else int(nrows)
        self.row_names = None if row_names is None else [str(name) for name in row_names]
        self.classes = {}

    def __len__(self):
        return self.nrows

    def __str__(self):
        return format_frame(self)


def _nrow(column):
    if isinstance(column, np.ndarray):
        if column.ndim == 0:
            return 1
        return int(column.shape[0])
    if isinstance(column, (Factor, Posixct, Matrix, DataFrame)):
        return len(column)
    if isinstance(column, str):
        raise TypeError("a character column must be a list of strings, not one string")
    return len(column)


def _is_missing(value):
    return value is None


def _is_bool(value):
    return isinstance(value, (bool, np.bool_))


def _is_int(value):
    return isinstance(value, (int, np.integer)) and not _is_bool(value)


def _is_float(value):
    return isinstance(value, (float, np.floating))


def _kind_of_one(value):
    if isinstance(value, datetime):
        return "time"
    if isinstance(value, date):
        return "date"
    if _is_bool(value):
        return "logical"
    if isinstance(value, str):
        return "character"
    if _is_int(value):
        return "integer"
    if _is_float(value):
        return "double"
    if isinstance(value, (list, tuple, dict)):
        return "list"
    return "other"


def _atomic_kind(values):
    kinds = set()
    for value in values:
        if value is None:
            continue
        kinds.add(_kind_of_one(value))
    if not kinds or kinds == {"other"}:
        return "double"
    if "character" in kinds:
        return "character"
    if "list" in kinds:
        return "list"
    if "time" in kinds:
        return "time"
    if "date" in kinds:
        return "date"
    if "double" in kinds:
        return "double"
    if "integer" in kinds:
        return "integer"
    if "logical" in kinds:
        return "logical"
    return "double"


def _column_kind(column):
    if isinstance(column, Factor):
        return "factor"
    if isinstance(column, Posixct):
        return "time"
    if isinstance(column, Matrix):
        return "array" if column.data.ndim > 1 else "atomic"
    if isinstance(column, DataFrame):
        return "dataframe"
    if isinstance(column, np.ndarray):
        if column.ndim > 1:
            return "array"
        return _atomic_kind(column.tolist())
    if callable(column):
        return "closure"
    if isinstance(column, str):
        raise TypeError("a character column must be a list of strings, not one string")
    return _atomic_kind(column)


def _attributes_of(column):
    raw = getattr(column, "attributes", None)
    if not raw:
        return {}
    kept = dict(raw)
    for name in ("names", "class", "levels", "dim", "dimnames", "tzone"):
        kept.pop(name, None)
    return kept


def _make_names(names, prefix="X"):
    """Fill blank names with ``X1``, ``X2``, ... in the order they appear."""
    blanks = sum(name == "" for name in names)
    sequence = iter(range(1, blanks + 1))
    filled = []
    for name in names:
        if name == "":
            filled.append(f"{prefix}{next(sequence)}")
        else:
            filled.append(name)
    return filled


def _level_key(level):
    if level is None:
        return ("na",)
    return ("v", level)


def _unified_levels(frames, name):
    levels = []
    known = set()
    for frame in frames:
        column = frame.columns.get(name)
        if not isinstance(column, Factor):
            continue
        for level in column.levels:
            key = _level_key(level)
            if key not in known:
                known.add(key)
                levels.append(level)
    return levels


def _all_factors(frames, name):
    seen = False
    for frame in frames:
        if name not in frame.columns:
            continue
        seen = True
        if not isinstance(frame.columns[name], Factor):
            return False
    return seen


def _array_data(column):
    if isinstance(column, Matrix):
        return column.data
    if isinstance(column, np.ndarray) and column.ndim > 1:
        return column
    return None


def _tail(column):
    data = _array_data(column)
    if data is None:
        return None
    return tuple(int(size) for size in data.shape[1:])


class _Slot:
    def __init__(self, kind, nrows, attrs=None, r_class=None):
        self.kind = kind
        self.attrs = dict(attrs or {})
        self.r_class = r_class
        self.values = [None] * nrows

    def assign(self, start, stop, column):
        incoming = _coerce_atomic(column, self.kind)
        if self.kind == "integer" and _source_is_double(column):
            self.kind = "double"
            self.r_class = None
            self.values = [None if value is None else float(value) for value in self.values]
            incoming = _coerce_atomic(column, "double")
        width = stop - start
        if len(incoming) != width:
            raise ValueError(
                f"replacement has {len(incoming)} rows, data has {width}"
            )
        self.values[start:stop] = incoming

    def value(self):
        return self.values


class _FactorSlot:
    def __init__(self, levels, nrows, ordered, attrs):
        self.levels = list(levels)
        self.ordered = ordered
        self.attrs = dict(attrs or {})
        self.codes = [None] * nrows
        self._index = {_level_key(level): index for index, level in enumerate(self.levels, start=1)}

    def assign(self, start, stop, column):
        if not isinstance(column, Factor):
            raise ValueError("factor column assigned from a non-factor")
        width = stop - start
        if len(column.codes) != width:
            raise ValueError(f"replacement has {len(column.codes)} rows, data has {width}")
        mapped = []
        for code in column.codes:
            if code is None:
                mapped.append(None)
                continue
            label = column.levels[code - 1]
            mapped.append(self._index.get(_level_key(label)))
        self.codes[start:stop] = mapped

    def value(self):
        return Factor(self.codes, self.levels, ordered=self.ordered, attributes=self.attrs)


class _TimeSlot:
    def __init__(self, tzone, nrows, attrs):
        self.tzone = tzone
        self.attrs = dict(attrs or {})
        self.seconds = [None] * nrows

    def assign(self, start, stop, column):
        incoming = _as_seconds(column)
        width = stop - start
        if len(incoming) != width:
            raise ValueError(f"replacement has {len(incoming)} rows, data has {width}")
        self.seconds[start:stop] = incoming

    def value(self):
        return Posixct(self.seconds, tzone=self.tzone, attributes=self.attrs)


class _ArraySlot:
    def __init__(self, example, nrows, tail, attrs):
        self.attrs = dict(attrs or {})
        data = _array_data(example)
        self.dimnames = None
        self.dimnames_names = None
        if isinstance(example, Matrix):
            if example.dimnames is not None:
                self.dimnames = [None if item is None else list(item) for item in example.dimnames]
                self.dimnames[0] = None
            if example.dimnames_names is not None:
                self.dimnames_names = list(example.dimnames_names)
                self.dimnames_names[0] = ""
        shape = (nrows, *tail)
        self.data = np.empty(shape, dtype=object)
        self.data.fill(None)
        if data is not None and np.issubdtype(data.dtype, np.number):
            # Numeric array cells stay Python numbers. Missing rows stay None,
            # which is R's NA, including for an integer array.
            pass

    def assign(self, start, stop, column):
        incoming = _array_data(column)
        if incoming is None:
            raise ValueError("array column assigned from a non-array")
        if tuple(int(size) for size in incoming.shape[1:]) != tuple(int(size) for size in self.data.shape[1:]):
            raise ValueError("Array variable has inconsistent dims")
        block = np.empty((stop - start, *self.data.shape[1:]), dtype=object)
        raw = np.asarray(incoming)
        for index in np.ndindex(raw.shape):
            block[index] = _python_cell(raw[index])
        self.data[start:stop] = block

    def value(self):
        return Matrix(
            self.data,
            dimnames=self.dimnames,
            dimnames_names=self.dimnames_names,
            attributes=self.attrs,
        )


class _ListSlot:
    def __init__(self, nrows, attrs):
        self.attrs = dict(attrs or {})
        self.values = [None] * nrows

    def assign(self, start, stop, column):
        incoming = list(column)
        width = stop - start
        if len(incoming) != width:
            raise ValueError(f"replacement has {len(incoming)} rows, data has {width}")
        self.values[start:stop] = incoming

    def value(self):
        return self.values


def _python_cell(value):
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        return value
    if _is_bool(value):
        return bool(value)
    if _is_int(value):
        return int(value)
    if _is_float(value):
        number = float(value)
        if math.isnan(number):
            return float("nan")
        return number
    if isinstance(value, str):
        return value
    return value


def _source_is_double(column):
    if isinstance(column, np.ndarray) and column.ndim <= 1:
        return np.issubdtype(column.dtype, np.floating)
    if isinstance(column, (Factor, Posixct, Matrix, DataFrame)):
        return False
    return _atomic_kind(column) == "double"


def _coerce_atomic(column, kind):
    if isinstance(column, np.ndarray) and column.ndim <= 1:
        values = [_python_cell(value) for value in column.tolist()]
    elif isinstance(column, Factor):
        values = []
        for code in column.codes:
            if code is None:
                values.append(None)
            else:
                values.append(column.levels[code - 1])
    elif isinstance(column, Posixct):
        values = list(column.seconds)
    else:
        values = list(column)
    if kind == "character":
        return [_as_character_one(value) for value in values]
    if kind == "double":
        return [_as_double(value) for value in values]
    if kind == "integer":
        return [_as_integer(value) for value in values]
    if kind == "logical":
        return [_as_logical(value) for value in values]
    if kind == "date":
        return [_as_date_day(value) for value in values]
    return values


def _as_double(value):
    if value is None:
        return None
    if isinstance(value, str):
        raise ValueError("invalid 'type' (character) of argument")
    if _is_bool(value):
        return float(int(value))
    if isinstance(value, datetime):
        return float(value.timestamp())
    if isinstance(value, date):
        return float(value.toordinal() - _EPOCH)
    number = float(value)
    if math.isnan(number):
        return float("nan")
    return number


def _as_integer(value):
    if value is None:
        return None
    if _is_bool(value):
        return int(value)
    if _is_float(value):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value)
    return int(value)


def _as_logical(value):
    if value is None:
        return None
    if _is_float(value) and math.isnan(value):
        return None
    return bool(value)


def _as_date_day(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return float(value.date().toordinal() - _EPOCH)
    if isinstance(value, date):
        return float(value.toordinal() - _EPOCH)
    return _as_double(value)


def _as_character_one(value):
    if value is None:
        return None
    if isinstance(value, Factor):
        return None
    if _is_bool(value):
        return "TRUE" if bool(value) else "FALSE"
    if _is_float(value):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return _format_r_real(float(value))
    if _is_int(value):
        return str(int(value))
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _format_r_real(value):
    """Fifteen significant digits, the way R prints a double as text."""
    if value == 0:
        return "0"
    text = format(value, ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        return f"{mantissa}e{int(exponent):+03d}"
    return text


def _as_seconds(column):
    if isinstance(column, Posixct):
        return [None if value is None else float(value) for value in column.seconds]
    if isinstance(column, np.ndarray):
        column = column.tolist()
    seconds = []
    for value in column:
        if value is None:
            seconds.append(None)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            seconds.append(float(value.timestamp()))
        elif _is_float(value) or _is_int(value):
            seconds.append(float(value))
        else:
            raise TypeError("cannot coerce column to POSIXct")
    return seconds


def _tzone_of(column):
    if isinstance(column, Posixct):
        return column.tzone
    return None


def _allocate(example, nrows, frames, name):
    if isinstance(example, (DataFrame, dict)):
        raise ValueError(f"Data frame column '{name}' not supported by rbind.fill")
    if callable(example) and not isinstance(example, type):
        raise ValueError("vector: cannot make a vector of mode 'closure'.")
    kind = _column_kind(example)
    if kind == "closure":
        raise ValueError("vector: cannot make a vector of mode 'closure'.")
    attrs = _attributes_of(example)
    if kind == "array":
        tails = []
        for frame in frames:
            if name not in frame.columns:
                continue
            tail = _tail(frame.columns[name])
            tails.append(tail)
        unique = []
        for tail in tails:
            if tail not in unique:
                unique.append(tail)
        if len(unique) > 1:
            raise ValueError(f"Array variable {name} has inconsistent dims")
        return _ArraySlot(example, nrows, unique[0], attrs)
    if kind == "factor" or (isinstance(example, Factor) and _all_factors(frames, name)):
        if _all_factors(frames, name):
            levels = _unified_levels(frames, name)
            ordered = bool(getattr(example, "ordered", False))
            return _FactorSlot(levels, nrows, ordered, attrs)
        return _Slot("character", nrows, attrs, r_class=None)
    if kind == "time" or isinstance(example, Posixct):
        return _TimeSlot(_tzone_of(example), nrows, attrs)
    if kind == "date":
        slot = _Slot("date", nrows, attrs, r_class=["Date"])
        return slot
    if kind == "list":
        return _ListSlot(nrows, attrs)
    if kind == "atomic":
        kind = _atomic_kind(_coerce_atomic(example, "double"))
    r_class = ["Date"] if kind == "date" else None
    if kind == "date":
        return _Slot("date", nrows, attrs, r_class=r_class)
    return _Slot(kind, nrows, attrs, r_class=None)


def rbind_fill(*args):
    """Bind data frames by row and fill columns that are not in every frame.

    ``args`` are frames. A frame is a :class:`DataFrame` or a dict of
    columns. The first argument may be a list of frames, and then the
    other arguments are ignored. ``None`` is dropped. No inputs, or only
    ``None``, returns ``None``. One remaining frame is returned unchanged.
    """
    if len(args) == 0:
        return None
    if isinstance(args[0], (list, tuple)):
        sources = list(args[0])
    else:
        sources = list(args)
    sources = [item for item in sources if item is not None]
    if len(sources) == 0:
        return None
    frames = []
    for item in sources:
        if isinstance(item, DataFrame):
            frames.append(item)
            continue
        if isinstance(item, dict):
            frames.append(DataFrame(item))
            continue
        raise ValueError("All inputs to rbind.fill must be data.frames")
    if len(frames) == 1:
        return frames[0]

    rows = [len(frame) for frame in frames]
    nrows = sum(rows)
    order = []
    first = {}
    for frame in frames:
        for name in frame.columns:
            if name not in first:
                first[name] = frame.columns[name]
                order.append(name)
    if not order:
        return DataFrame({}, nrows=nrows)

    slots = {}
    for name in order:
        slots[name] = _allocate(first[name], nrows, frames, name)

    offset = 0
    for frame, count in zip(frames, rows):
        for name, column in frame.columns.items():
            slots[name].assign(offset, offset + count, column)
        offset += count

    built = {}
    attrs = {}
    classes = {}
    for name in order:
        built[name] = slots[name].value()
        slot_attrs = getattr(slots[name], "attrs", None)
        if slot_attrs:
            attrs[name] = dict(slot_attrs)
        r_class = getattr(slots[name], "r_class", None)
        if r_class:
            classes[name] = list(r_class)
    final_names = _make_names(list(built))
    renamed = {}
    renamed_attrs = {}
    renamed_classes = {}
    for old, new in zip(order, final_names):
        renamed[new] = built[old]
        if old in attrs:
            renamed_attrs[new] = attrs[old]
        if old in classes:
            renamed_classes[new] = classes[old]
    result = DataFrame(renamed, nrows=nrows)
    result.attrs = renamed_attrs
    result.classes = renamed_classes
    return result


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
        if value is None:
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


def _factor_cells(column):
    cells = []
    for code in column.codes:
        if code is None:
            cells.append("<NA>")
        else:
            label = column.levels[code - 1]
            cells.append("<NA>" if label is None else str(label))
    return cells


def _character_cells(values):
    return ["<NA>" if value is None else str(value) for value in values]


def _logical_cells(values):
    cells = []
    for value in values:
        if value is None:
            cells.append("NA")
        elif value:
            cells.append("TRUE")
        else:
            cells.append("FALSE")
    return cells


def _column_cells(column):
    if isinstance(column, Factor):
        return _factor_cells(column)
    if isinstance(column, Posixct):
        return _numeric_cells(column.seconds)
    if isinstance(column, Matrix):
        if column.data.ndim == 1:
            flat = [_python_cell(value) for value in column.data.tolist()]
        else:
            flat = []
            for row in column.data:
                flat.append(" ".join(_cell_token(_python_cell(value)) for value in row))
            return flat
        return _cells_for_values(flat)
    if isinstance(column, np.ndarray):
        return _cells_for_values([_python_cell(value) for value in column.reshape(-1).tolist()])
    return _cells_for_values(list(column))


def _cell_token(value):
    if value is None:
        return "NA"
    if _is_float(value) and math.isnan(value):
        return "NaN"
    if _is_bool(value):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    return str(value)


def _cells_for_values(values):
    if not values:
        return []
    sample = next((value for value in values if value is not None and not (_is_float(value) and math.isnan(value))), None)
    if sample is None or _is_float(sample) or _is_int(sample):
        if any(_is_bool(value) for value in values):
            return _logical_cells(values)
        if any(isinstance(value, str) for value in values):
            return _character_cells([None if value is None else str(value) for value in values])
        return _numeric_cells(values)
    if _is_bool(sample):
        return _logical_cells(values)
    if isinstance(sample, str):
        return _character_cells(values)
    return ["" if value is None else str(value) for value in values]


def format_frame(frame):
    """Print a frame the way R prints a data frame."""
    names = list(frame.columns)
    nrow = len(frame)
    if not names:
        noun = "row" if nrow == 1 else "rows"
        return f"data frame with 0 columns and {nrow} {noun}"
    if nrow == 0:
        shown = " ".join(names)
        return f"[1] {shown}\n<0 rows> (or 0-length row.names)"
    formatted = []
    for name in names:
        cells = _column_cells(frame.columns[name])
        width = max([len(name), *(len(cell) for cell in cells)])
        formatted.append((name.rjust(width), [cell.rjust(width) for cell in cells]))
    labels = frame.row_names if frame.row_names is not None else [str(index) for index in range(1, nrow + 1)]
    row_width = max(len(label) for label in labels)
    lines = [" " * row_width + " " + " ".join(title for title, _cells in formatted)]
    for index in range(nrow):
        body = " ".join(cells[index] for _title, cells in formatted)
        lines.append(labels[index].ljust(row_width) + " " + body)
    return "\n".join(lines)
