"""Count combinations the way plyr 1.8.9 does.

``count`` is R. The grouping ids are ``ninteraction`` (``id``), and a weight
uses ``sum`` on those ids. Rcpp's ``split_indices`` is not used. Character
order follows the ICU collator R uses for ``sort``, not code-point order.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import math
import os
import sys
from datetime import date, datetime

import numpy as np


_KEYWORDS = {
    "if",
    "else",
    "repeat",
    "while",
    "function",
    "for",
    "in",
    "next",
    "break",
    "TRUE",
    "FALSE",
    "NULL",
    "Inf",
    "NaN",
    "NA",
    "NA_integer_",
    "NA_real_",
    "NA_complex_",
    "NA_character_",
}

_INT_MAX = 2147483647
_ID_LIMIT = 2**31


class Factor:
    """Factor values in level order. Missing entries are ``None``."""

    def __init__(self, values, levels):
        self.levels = [str(level) for level in levels]
        self.values = [_as_factor_value(value) for value in values]

    def __len__(self):
        return len(self.values)


def _as_factor_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value)


class DataFrame:
    """Column-oriented frame. Columns keep the types ``count`` was given."""

    def __init__(self, columns):
        self.columns = {}
        for name, values in columns.items():
            self.columns[str(name)] = values
        self._check_rows()

    def _check_rows(self):
        lengths = {_length(column) for column in self.columns.values()}
        if len(lengths) > 1:
            raise ValueError("columns must have one common length")

    def __len__(self):
        if not self.columns:
            return 0
        return _length(next(iter(self.columns.values())))

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.columns[key]
        if isinstance(key, slice):
            return DataFrame(
                {name: _slice_column(column, key) for name, column in self.columns.items()}
            )
        raise TypeError("column lookup takes a name or a row slice")

    def __str__(self):
        return format_frame(self)


def _length(column):
    if isinstance(column, Factor):
        return len(column.values)
    return len(column)


def _slice_column(column, key):
    if isinstance(column, Factor):
        return Factor(column.values[key], column.levels)
    return list(column[key])


def _normalize_one(value):
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value)
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    return value


def _normalize(values):
    if isinstance(values, Factor):
        return values
    if isinstance(values, str):
        raise TypeError("a character column must be a list of strings, not one string")
    return [_normalize_one(value) for value in values]


def _collation_locale():
    for variable in ("LC_ALL", "LC_COLLATE", "LANG"):
        value = os.environ.get(variable)
        if value and value.lower() not in {"c", "posix"}:
            return value.split(".")[0]
    return "en_US"


class _Collator:
    """ICU collator. R's shell ``sort`` for character vectors calls this."""

    def __init__(self):
        path = ctypes.util.find_library("icui18n")
        if not path:
            path = "libicui18n.so.76"
        library = ctypes.CDLL(path)
        version = "76"
        stem = os.path.basename(path)
        if ".so." in stem:
            version = stem.rsplit(".so.", 1)[1].split(".")[0]
        open_name = f"ucol_open_{version}"
        compare_name = f"ucol_strcollUTF8_{version}"
        close_name = f"ucol_close_{version}"
        opener = getattr(library, open_name)
        opener.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
        opener.restype = ctypes.c_void_p
        compare = getattr(library, compare_name)
        compare.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int),
        ]
        compare.restype = ctypes.c_int
        closer = getattr(library, close_name)
        closer.argtypes = [ctypes.c_void_p]
        status = ctypes.c_int(0)
        collator = opener(_collation_locale().encode(), ctypes.byref(status))
        if not collator or status.value > 0:
            raise OSError(f"ucol_open failed for {_collation_locale()}")
        self._compare = compare
        self._closer = closer
        self._collator = collator
        self._keys = {}

    def before(self, left, right):
        status = ctypes.c_int(0)
        raw_left = left.encode()
        raw_right = right.encode()
        return (
            self._compare(
                self._collator,
                raw_left,
                len(raw_left),
                raw_right,
                len(raw_right),
                ctypes.byref(status),
            )
            < 0
        )


_COLLATOR = None


def _collator():
    global _COLLATOR
    if _COLLATOR is None:
        _COLLATOR = _Collator()
    return _COLLATOR


def _make_one_name(name):
    if name is None:
        name = "NA"
    else:
        name = str(name)
    prefix = False
    if name == "":
        prefix = True
    elif not (name[0].isalpha() or name[0] == "."):
        prefix = True
    elif name[0] == "." and len(name) > 1 and name[1] in "0123456789":
        prefix = True
    translated = []
    for character in name:
        if character.isalnum() or character in "._":
            translated.append(character)
        else:
            translated.append(".")
    text = "".join(translated)
    if prefix:
        text = "X" + text
    if text == "":
        text = "X"
    if text in _KEYWORDS:
        text = text + "."
    return text


def _make_unique(names):
    """R ``make.unique``. Later original names stay reserved."""
    counts = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
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


def _make_names(names):
    return _make_unique([_make_one_name(name) for name in names])


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _is_missing_number(value):
    return value is None or _is_nan(value)


def _number_group_key(value):
    if value is None:
        return ("na",)
    if _is_nan(value):
        return ("nan",)
    number = float(value)
    if number == 0.0:
        number = 0.0
    return ("n", number)


def _column_values(column):
    if isinstance(column, Factor):
        return column.values
    return column


def _sorted_unique(column):
    """Levels in ``sort(unique(x), na.last = TRUE)`` order.

    ``NA`` and ``NaN`` are both missing, so they stay in first-seen order
    after the finite values. ``-0`` and ``0`` are one level.
    """
    if isinstance(column, Factor):
        seen = []
        known = set()
        for value in column.values:
            marker = ("na",) if value is None else ("v", value)
            if marker not in known:
                known.add(marker)
                seen.append(value)
        present = [value for value in seen if value is not None]
        missing = [value for value in seen if value is None]
        positions = {level: index for index, level in enumerate(column.levels)}
        present.sort(key=lambda value: positions.get(value, len(positions)))
        return present + missing

    values = _column_values(column)
    sample = next((value for value in values if value is not None and not _is_nan(value)), None)
    seen = []
    known = set()
    for value in values:
        if isinstance(sample, str) or (sample is None and isinstance(value, str)):
            key = ("na",) if value is None else ("c", value)
        elif isinstance(sample, bool) or isinstance(value, bool):
            key = ("na",) if value is None else ("b", bool(value))
        elif isinstance(sample, (date, datetime)) or isinstance(value, (date, datetime)):
            key = ("na",) if value is None else ("d", value.isoformat())
        elif _is_missing_number(value) or isinstance(sample, (int, float)) or sample is None:
            key = _number_group_key(value)
        else:
            key = ("na",) if value is None else ("o", repr(value))
        if key not in known:
            known.add(key)
            seen.append(value)

    if isinstance(sample, str):
        present = [value for value in seen if value is not None]
        missing = [value for value in seen if value is None]
        collator = _collator()
        present.sort(key=lambda value: _SortKey(collator, value))
        return present + missing
    if isinstance(sample, bool):
        present = [value for value in seen if value is not None]
        missing = [value for value in seen if value is None]
        present.sort(key=lambda value: bool(value))
        return present + missing
    if isinstance(sample, datetime):
        present = [value for value in seen if value is not None]
        missing = [value for value in seen if value is None]
        present.sort(key=lambda value: value.timestamp())
        return present + missing
    if isinstance(sample, date):
        present = [value for value in seen if value is not None]
        missing = [value for value in seen if value is None]
        present.sort(key=lambda value: value.toordinal())
        return present + missing
    present = [value for value in seen if not _is_missing_number(value)]
    missing = [value for value in seen if _is_missing_number(value)]
    present.sort(key=lambda value: float(value))
    return present + missing


class _SortKey:
    def __init__(self, collator, text):
        self._collator = collator
        self._text = text

    def __lt__(self, other):
        return self._collator.before(self._text, other._text)


def _id_var(column):
    """1-based ids in sorted-unique order, and how many levels occurred."""
    if _length(column) == 0:
        return [], 0
    levels = _sorted_unique(column)
    mapping = {}
    for index, level in enumerate(levels, start=1):
        mapping[_number_group_key(level) if not isinstance(column, Factor) and not isinstance(level, str) and not isinstance(level, bool) and not isinstance(level, (date, datetime)) else _level_key(column, level)] = index
    # The branch above is hard to read; rebuild the map with one key function.
    mapping = {_level_key(column, level): index for index, level in enumerate(levels, start=1)}
    values = column.values if isinstance(column, Factor) else column
    ids = [mapping[_level_key(column, value)] for value in values]
    return ids, len(levels)


def _level_key(column, value):
    if isinstance(column, Factor):
        return ("na",) if value is None else ("f", value)
    if isinstance(value, str):
        return ("c", value)
    if isinstance(value, bool):
        return ("b", value)
    if isinstance(value, datetime):
        return ("t", value.isoformat())
    if isinstance(value, date):
        return ("d", value.isoformat())
    if value is None or _is_nan(value) or isinstance(value, (int, float)):
        return _number_group_key(value)
    return ("o", repr(value))


def _remap_sorted(ids):
    return _id_var(ids)


def _interaction(columns, nrow):
    kept = [column for column in columns if _length(column) != 0]
    if not kept:
        return list(range(1, nrow + 1)), nrow
    if len(kept) == 1:
        return _id_var(kept[0])
    # The last column varies fastest, matching ``rev(lapply(...))``.
    parts = [_id_var(column) for column in reversed(kept)]
    distinct = [count for _ids, count in parts]
    product = 1
    overflow = False
    for count in distinct:
        product *= count
        if product > _ID_LIMIT:
            overflow = True
            break
    if overflow:
        keys = []
        width = _length(kept[0])
        for row in range(width):
            keys.append("\r".join(str(ids[row]) for ids, _count in parts))
        first = {}
        combined = []
        for key in keys:
            if key not in first:
                first[key] = len(first) + 1
            combined.append(first[key])
        return _remap_sorted(combined)
    steps = [1]
    for count in distinct[:-1]:
        steps.append(steps[-1] * count)
    width = _length(kept[0])
    combined = []
    for row in range(width):
        value = 1
        for (ids, _count), step in zip(parts, steps):
            value += (ids[row] - 1) * step
        combined.append(value)
    return _remap_sorted(combined)


def _tabulate(ids, total):
    if total <= 0:
        return []
    counts = np.bincount(np.asarray(ids, dtype=np.int64), minlength=total + 1)
    output = []
    for count in counts[1:]:
        if int(count) > _INT_MAX:
            output.append(None)
        else:
            output.append(int(count))
    return output


def _weighted(ids, weights, total):
    sums = [np.longdouble(0) for _ in range(total)]
    state = ["ok"] * total
    for group, weight in zip(ids, weights):
        slot = group - 1
        if weight is None:
            state[slot] = "na"
            continue
        if isinstance(weight, float) and math.isnan(weight):
            if state[slot] != "na":
                state[slot] = "nan"
            continue
        if isinstance(weight, bool):
            sums[slot] += np.longdouble(int(weight))
            continue
        if not isinstance(weight, (int, float)):
            raise ValueError("invalid 'type' (character) of argument")
        sums[slot] += np.longdouble(weight)
    output = []
    for total_value, flag in zip(sums, state):
        if flag == "na":
            output.append(None)
        elif flag == "nan":
            output.append(float("nan"))
        else:
            output.append(float(total_value))
    return output


def _first_rows(ids, total):
    found = {}
    for index, group in enumerate(ids):
        if group not in found:
            found[group] = index
    return [found[group] for group in range(1, total + 1)]


def _take(column, indices):
    if isinstance(column, Factor):
        return Factor([column.values[index] for index in indices], column.levels)
    return [column[index] for index in indices]


class _Parser:
    def __init__(self, text):
        self.text = text
        self.size = len(text)
        self.index = 0

    def parse(self):
        node = self._parse_sum()
        self._skip()
        if self.index != self.size:
            raise ValueError(f"could not parse {self.text!r}")
        return node

    def _skip(self):
        while self.index < self.size and self.text[self.index].isspace():
            self.index += 1

    def _peek(self):
        self._skip()
        if self.index >= self.size:
            return ""
        return self.text[self.index]

    def _parse_sum(self):
        node = self._parse_prod()
        while True:
            operator = self._peek()
            if operator != "+" and operator != "-":
                break
            self.index += 1
            right = self._parse_prod()
            node = ("bin", operator, node, right)
        return node

    def _parse_prod(self):
        node = self._parse_unary()
        while True:
            operator = self._peek()
            if operator != "*" and operator != "/":
                break
            self.index += 1
            right = self._parse_unary()
            node = ("bin", operator, node, right)
        return node

    def _parse_unary(self):
        operator = self._peek()
        if operator == "+" or operator == "-":
            self.index += 1
            node = self._parse_unary()
            if operator == "+":
                return node
            return ("unary", "-", node)
        return self._parse_pow()

    def _parse_pow(self):
        node = self._parse_primary()
        if self._peek() == "^":
            self.index += 1
            right = self._parse_unary()
            return ("bin", "^", node, right)
        return node

    def _parse_primary(self):
        self._skip()
        if self.index >= self.size:
            raise ValueError(f"could not parse {self.text!r}")
        character = self.text[self.index]
        if character == "(":
            self.index += 1
            node = self._parse_sum()
            if self._peek() != ")":
                raise ValueError(f"could not parse {self.text!r}")
            self.index += 1
            return node
        if character.isdigit() or character == ".":
            return ("num", self._number())
        if character == "`":
            return ("name", self._backtick())
        if character.isalpha() or character == "." or character == "_":
            name = self._name()
            if self._peek() == "(":
                self.index += 1
                args = []
                if self._peek() != ")":
                    while True:
                        args.append(self._parse_sum())
                        if self._peek() == ",":
                            self.index += 1
                            continue
                        break
                if self._peek() != ")":
                    raise ValueError(f"could not parse {self.text!r}")
                self.index += 1
                return ("call", name, args)
            return ("name", name)
        raise ValueError(f"could not parse {self.text!r}")

    def _name(self):
        start = self.index
        self.index += 1
        while self.index < self.size:
            character = self.text[self.index]
            if character.isalnum() or character in "._":
                self.index += 1
                continue
            break
        return self.text[start:self.index]

    def _backtick(self):
        self.index += 1
        start = self.index
        while self.index < self.size and self.text[self.index] != "`":
            self.index += 1
        name = self.text[start:self.index]
        if self.index < self.size:
            self.index += 1
        return name

    def _number(self):
        start = self.index
        while self.index < self.size and (self.text[self.index].isdigit() or self.text[self.index] in ".eE+-"):
            if self.text[self.index] in "+-" and self.text[self.index - 1] not in "eE":
                break
            self.index += 1
        if self.index < self.size and self.text[self.index] in "Ll":
            self.index += 1
            return int(self.text[start:self.index - 1])
        text = self.text[start:self.index]
        if any(mark in text for mark in ".eE"):
            return float(text)
        return int(text)


def _split_formula(node):
    if node[0] == "unary" and node[1] == "-":
        return [node]
    if node[0] == "bin" and node[1] in {"+", "*", "~"}:
        return _split_formula(node[2]) + _split_formula(node[3])
    if node[0] == "bin" and node[1] == "-":
        right = _split_formula(node[3])
        negated = [("unary", "-", part) for part in right]
        return _split_formula(node[2]) + negated
    return [node]


def _parse_vars(spec):
    """Return expression nodes and optional user names."""
    if isinstance(spec, str):
        text = spec.strip()
        if text.startswith("~"):
            body = text[1:].strip()
            if body == "":
                return []
            node = _Parser(body).parse()
            return [(None, part) for part in _split_formula(node)]
        return [(None, _Parser(text).parse())]
    if isinstance(spec, dict):
        return [(str(name), _Parser(str(value)).parse()) for name, value in spec.items()]
    pairs = []
    for item in spec:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], str):
            pairs.append((None if item[0] in (None, "") else str(item[0]), _Parser(item[1]).parse()))
        else:
            pairs.extend(_parse_vars(item))
    return pairs


def _deparse(node):
    kind = node[0]
    if kind == "name":
        return node[1]
    if kind == "num":
        value = node[1]
        if isinstance(value, float):
            return _format_number(value)
        return str(value)
    if kind == "unary":
        inner = _deparse(node[2])
        if node[2][0] == "bin":
            return f"-({inner})"
        return f"-{inner}"
    if kind == "call":
        args = ", ".join(_deparse(arg) for arg in node[2])
        return f"{node[1]}({args})"
    if kind == "bin":
        return f"{_deparse(node[2])} {node[1]} {_deparse(node[3])}"
    raise ValueError("cannot deparse expression")


def _lookup(frame, name):
    if name not in frame.columns:
        raise ValueError(f"object '{name}' not found")
    return frame.columns[name]


def _as_series(value, width):
    if isinstance(value, Factor):
        series = value.values
    elif isinstance(value, list):
        series = value
    else:
        series = [value]
    if len(series) == 1 and width != 1:
        return series * width
    if width == 1 and len(series) != 1:
        return series
    if len(series) != width:
        if width == 0:
            return []
        if len(series) == 0 or width % len(series) != 0:
            raise ValueError("longer object length is not a multiple of shorter object length")
        times = width // len(series)
        return series * times
    return series


def _binary_number(operator, left, right):
    if left is None or right is None:
        return None
    if _is_nan(left) or _is_nan(right):
        return float("nan")
    left = float(left)
    right = float(right)
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        if right == 0.0:
            if left == 0.0:
                return float("nan")
            return math.copysign(float("inf"), left * right if right == 0 else left)
        return left / right
    if operator == "^":
        try:
            return float(left**right)
        except ValueError:
            return float("nan")
    raise ValueError(f"unknown operator {operator}")


def _eval_node(node, frame):
    kind = node[0]
    width = len(frame)
    if kind == "name":
        return _lookup(frame, node[1])
    if kind == "num":
        return [node[1]]
    if kind == "unary":
        series = _as_series(_eval_node(node[2], frame), width if width else 1)
        output = []
        for value in series:
            if value is None:
                output.append(None)
            elif _is_nan(value):
                output.append(float("nan"))
            else:
                output.append(-float(value))
        return output
    if kind == "bin":
        left = _as_series(_eval_node(node[2], frame), width if width else 1)
        right = _as_series(_eval_node(node[3], frame), max(len(left), width if width else 1))
        if len(left) == 1 and len(right) != 1:
            left = left * len(right)
        elif len(right) == 1 and len(left) != 1:
            right = right * len(left)
        if len(left) != len(right):
            raise ValueError("longer object length is not a multiple of shorter object length")
        return [_binary_number(node[1], a, b) for a, b in zip(left, right)]
    if kind == "call":
        if node[1] not in {"log", "exp", "sqrt", "abs"}:
            raise ValueError(f"object '{node[1]}' not found")
        if len(node[2]) != 1:
            raise ValueError(f"{node[1]} takes one argument")
        series = _as_series(_eval_node(node[2][0], frame), width if width else 1)
        output = []
        function = {"log": math.log, "exp": math.exp, "sqrt": math.sqrt, "abs": abs}[node[1]]
        for value in series:
            if value is None:
                output.append(None)
                continue
            if _is_nan(value):
                output.append(float("nan"))
                continue
            try:
                output.append(float(function(float(value))))
            except ValueError:
                output.append(float("nan"))
        return output
    raise ValueError("cannot evaluate expression")


def _eval_spec(spec, frame):
    if isinstance(spec, int) and not isinstance(spec, bool):
        return _subset_columns(frame, [spec])
    if (
        isinstance(spec, (list, tuple))
        and spec
        and all(isinstance(item, int) and not isinstance(item, bool) for item in spec)
    ):
        return _subset_columns(frame, list(spec))
    pairs = _parse_vars(spec)
    if not pairs:
        raise ValueError("columns must have one common length")
    columns = {}
    raw_names = []
    for user_name, node in pairs:
        raw_names.append(_deparse(node) if user_name is None else user_name)
        columns[raw_names[-1]] = _normalize(_as_list(_eval_node(node, frame)))
    lengths = {_length(column) for column in columns.values()}
    if len(lengths) != 1:
        raise ValueError("columns must have one common length")
    # Temporary names may collide before make.names. Store them in order.
    ordered = {}
    for index, (name, column) in enumerate(columns.items()):
        ordered[f"__{index}__{name}"] = column
    frame_out = DataFrame(ordered)
    frame_out.raw_names = raw_names
    return frame_out


def _as_list(value):
    if isinstance(value, Factor):
        return value
    if isinstance(value, list):
        return value
    return [value]


def _subset_columns(frame, indices):
    names = list(frame.columns)
    if any(index < 0 for index in indices):
        if any(index > 0 for index in indices):
            raise ValueError("only 0's may be mixed with negative subscripts")
        dropped = {abs(index) for index in indices if index != 0}
        kept = [name for index, name in enumerate(names, start=1) if index not in dropped]
        return DataFrame({name: frame.columns[name] for name in kept})
    columns = {}
    raw_names = []
    for index in indices:
        if index == 0:
            continue
        if index < 1 or index > len(names):
            raise ValueError("subscript out of bounds")
        raw_names.append(names[index - 1])
        columns[f"{names[index - 1]}#{len(raw_names)}"] = frame.columns[names[index - 1]]
    selected = DataFrame(columns)
    selected.raw_names = raw_names
    return selected


def _frame_from_atomic(values):
    if isinstance(values, np.ndarray) and values.ndim == 2:
        columns = {}
        colnames = getattr(values, "colnames", None)
        for index in range(values.shape[1]):
            if colnames is None:
                name = f"x.{index + 1}"
            else:
                name = f"x.{colnames[index]}"
            columns[name] = _normalize(values[:, index])
        return DataFrame(columns)
    if isinstance(values, Factor):
        return DataFrame({"x": values})
    return DataFrame({"x": _normalize(values)})


def _as_frame(df):
    if isinstance(df, DataFrame):
        return df
    if isinstance(df, dict):
        return DataFrame({str(name): _normalize(values) for name, values in df.items()})
    if isinstance(df, str):
        raise TypeError("df must be a data frame or an atomic vector")
    return _frame_from_atomic(df)


def _column_list(frame):
    names = getattr(frame, "raw_names", None)
    columns = list(frame.columns.values())
    if names is None:
        names = list(frame.columns)
    return names, columns


def _format_number(value):
    if value is None:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e16:
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    text = format(float(value), ".7g")
    return text


def _cell_text(value, kind):
    if kind == "character":
        if value is None:
            return "<NA>"
        return str(value)
    if kind == "logical":
        if value is None:
            return "NA"
        return "TRUE" if value else "FALSE"
    if kind == "date":
        if value is None:
            return "NA"
        return value.isoformat()[:10] if isinstance(value, datetime) else value.isoformat()
    return _format_number(value)


def _column_kind(column):
    if isinstance(column, Factor):
        return "character"
    for value in column:
        if value is None or _is_nan(value):
            continue
        if isinstance(value, bool):
            return "logical"
        if isinstance(value, str):
            return "character"
        if isinstance(value, (date, datetime)):
            return "date"
        return "number"
    return "number"


def format_frame(frame):
    names, columns = _column_list(frame)
    display_names = _make_names(names + ["freq"])[:-1] if False else names
    # ``count`` already ran make.names. Print the stored names.
    display_names = list(frame.columns)
    nrow = len(frame)
    if nrow == 0:
        if not display_names:
            body = "[1] \n<0 rows> (or 0-length row.names)"
            return body
        header = " ".join(display_names)
        return f"[1] {header}\n<0 rows> (or 0-length row.names)"
    kinds = [_column_kind(column) for column in columns]
    texts = []
    for column, kind in zip(columns, kinds):
        values = column.values if isinstance(column, Factor) else column
        texts.append([_cell_text(value, kind) for value in values])
    widths = []
    for name, cells in zip(display_names, texts):
        widths.append(max([len(name), *(len(cell) for cell in cells)]))
    row_width = len(str(nrow))
    lines = []
    header_cells = [name.rjust(width) for name, width in zip(display_names, widths)]
    lines.append(" " * row_width + " " + " ".join(header_cells))
    for row in range(nrow):
        cells = [texts[col][row].rjust(widths[col]) for col in range(len(columns))]
        lines.append(str(row + 1).ljust(row_width) + " " + " ".join(cells))
    return "\n".join(lines)


def count(df, vars=None, wt_var=None):
    """Count combinations of ``vars``.

    ``df`` is a :class:`DataFrame`, a dict of columns, or an atomic vector.
    An atomic vector is one column named ``x``. ``vars`` selects columns by
    name, by a 1-based index, or by an expression such as ``log(cyl)``. A
    string that starts with ``~`` is split on ``+`` the way a formula is.
    ``wt_var`` sums that column instead of counting rows. A column named
    ``freq`` is used as the weight when ``wt_var`` is omitted.
    """
    frame = _as_frame(df)
    if vars is not None:
        selected = _eval_spec(vars, frame)
        group_names, group_columns = _column_list(selected)
    else:
        group_names = list(frame.columns)
        group_columns = [frame.columns[name] for name in group_names]
    ids, total = _interaction(group_columns, len(frame) if not group_columns else _length(group_columns[0]) if group_columns else len(frame))
    if not group_columns:
        nrow = len(frame)
        ids, total = list(range(1, nrow + 1)), nrow
    if wt_var is None and "freq" in frame.columns:
        sys.stderr.write("Using freq as weighting variable\n")
        wt_var = "freq"
    if wt_var is not None:
        if isinstance(wt_var, (list, tuple)) and not (
            wt_var and all(isinstance(item, int) and not isinstance(item, bool) for item in wt_var)
        ):
            if len(list(wt_var)) > 1 and not isinstance(wt_var, str):
                raise ValueError("wt_var must be a single variable")
        if isinstance(wt_var, str) and wt_var.strip().startswith("~"):
            parts = _parse_vars(wt_var)
            if len(parts) > 1:
                raise ValueError("wt_var must be a single variable")
        if isinstance(wt_var, (list, tuple)) and wt_var and all(
            isinstance(item, int) and not isinstance(item, bool) for item in wt_var
        ):
            if len(wt_var) > 1:
                raise ValueError("wt_var must be a single variable")
        if isinstance(wt_var, dict) and len(wt_var) > 1:
            raise ValueError("wt_var must be a single variable")
        weight_frame = _eval_spec(wt_var, frame)
        _weight_names, weight_columns = _column_list(weight_frame)
        if len(weight_columns) != 1:
            raise ValueError("wt_var must be a single variable")
        weights = weight_columns[0]
        if isinstance(weights, Factor):
            raise ValueError("invalid 'type' (character) of argument")
        freq = _weighted(ids, weights, total)
    else:
        freq = _tabulate(ids, total)
    indices = _first_rows(ids, total) if total else []
    kept_names = []
    kept_columns = []
    for name, column in zip(group_names, group_columns):
        kept_names.append(name)
        kept_columns.append(_take(column, indices))
    kept_names.append("freq")
    kept_columns.append(freq)
    final_names = _make_names(kept_names)
    return DataFrame({name: column for name, column in zip(final_names, kept_columns)})
