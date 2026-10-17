"""Edition 2 compare() and the waldo-style differences expect_equal uses in edition 3.

The waldo package is not translated. This is the slice testthat calls:
type mismatches, numeric tolerance, and short atomic diffs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


TOLERANCE = math.sqrt(2.220446049250313e-16)  # .Machine$double.eps^0.5


@dataclass
class Comparison:
    equal: bool
    message: str

    def __iter__(self):
        yield self.equal
        yield self.message


def comparison(equal: bool = True, message: str = "Equal") -> Comparison:
    return Comparison(bool(equal), message if isinstance(message, str) else "\n".join(message))


def no_difference() -> Comparison:
    return comparison()


def difference(message: str) -> Comparison:
    return comparison(False, message)


def testthat_tolerance() -> float:
    return TOLERANCE


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_floats(value):
    if _is_number(value):
        return [float(value)]
    if isinstance(value, (list, tuple)) and value and all(_is_number(item) or _missing(item) for item in value):
        return [float("nan") if _missing(item) else float(item) for item in value]
    return None


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _num_exact(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def _digits(values) -> int:
    cleaned = [abs(item) for item in values if item is not None and item != 0 and not math.isnan(item)]
    if not cleaned:
        return 0
    scale = -math.log10(min(cleaned))
    if scale <= 0:
        return 0
    return math.ceil(round(scale, 2))


def _min_digits(left, right, tolerance) -> int:
    diff = [abs(a - b) for a, b in zip(left, right)]
    count = _digits(diff)
    if tolerance is not None:
        count = min(count, _digits([tolerance]))
    return int(count) + 1


def num_equal(left, right, tolerance) -> bool:
    if len(left) != len(right):
        return False
    if any(_missing(a) != _missing(b) for a, b in zip(left, right)):
        return False
    same = []
    for a, b in zip(left, right):
        if _missing(a) and _missing(b):
            same.append(True)
        else:
            same.append(a == b)
    if tolerance is None or all(same):
        return all(same)
    x_diff = [a for a, ok in zip(left, same) if not ok]
    y_diff = [b for b, ok in zip(right, same) if not ok]
    avg_diff = sum(abs(a - b) for a, b in zip(x_diff, y_diff)) / len(x_diff)
    avg_y = sum(abs(item) for item in y_diff) / len(y_diff)
    if math.isfinite(avg_y) and avg_y > tolerance:
        avg_diff = avg_diff / avg_y
    return avg_diff < tolerance


def _align(cells: list[str], justify: str) -> list[str]:
    width = max(len(cell) for cell in cells)
    if justify == "right":
        return [cell.rjust(width) for cell in cells]
    return [cell.ljust(width) for cell in cells]


def _paired(x_label: str, y_label: str, x_value: str, y_value: str, justify: str) -> str:
    labels = _align([f"`{x_label}`:", f"`{y_label}`:"], justify)
    values = _align([x_value, y_value], justify)
    return "\n".join(f"{label} {value}" for label, value in zip(labels, values)) + "\n"


def waldo_compare(actual, expected, tolerance=None, ignore_attr: bool = False, x_arg="actual", y_arg="expected") -> list[str]:
    """Return waldo-style difference lines. An empty list means equal."""
    if _same(actual, expected, tolerance, ignore_attr):
        return []
    kind_a, kind_b = _friendly(actual), _friendly(expected)
    if kind_a != kind_b and not _numeric_pair(actual, expected, tolerance):
        short_a = _short(actual)
        short_b = _short(expected)
        return [f"`{x_arg}` is {kind_a}{short_a}\n`{y_arg}` is {kind_b}{short_b}\n"]
    left = _as_floats(actual)
    right = _as_floats(expected)
    if left is not None and right is not None:
        if tolerance is not None and num_equal(left, right, tolerance):
            return []
        digits = _min_digits(left, right, tolerance if tolerance is not None else TOLERANCE)
        if len(left) == len(right) == 1:
            return [_paired(x_arg, y_arg, _num_exact(left[0], digits), _num_exact(right[0], digits), "right")]
        return [_paired(x_arg, y_arg, _fmt_vec(left, digits), _fmt_vec(right, digits), "right")]
    if isinstance(actual, bool) and isinstance(expected, bool):
        return [_paired(x_arg, y_arg, "TRUE" if actual else "FALSE", "TRUE" if expected else "FALSE", "left")]
    if actual is None or expected is None:
        return [f"`{x_arg}` is {_friendly(actual)}{_short(actual)}\n`{y_arg}` is {_friendly(expected)}{_short(expected)}\n"]
    if isinstance(actual, str) and isinstance(expected, str):
        return [_paired(x_arg, y_arg, '"' + actual + '"', '"' + expected + '"', "left")]
    return [f"`{x_arg}` is {_friendly(actual)}{_short(actual)}\n`{y_arg}` is {_friendly(expected)}{_short(expected)}\n"]


def _numeric_pair(actual, expected, tolerance) -> bool:
    left, right = _as_floats(actual), _as_floats(expected)
    return left is not None and right is not None and tolerance is not None


def _same(actual, expected, tolerance, ignore_attr: bool) -> bool:
    if type(actual) is type(expected) and actual == expected:
        return True
    left, right = _as_floats(actual), _as_floats(expected)
    if left is not None and right is not None and tolerance is not None:
        return num_equal(left, right, tolerance)
    return False


def _friendly(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "a logical vector"
    if isinstance(value, int) and not isinstance(value, bool):
        return "an integer vector"
    if isinstance(value, float):
        return "a double vector"
    if isinstance(value, str):
        return "a character vector"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "a list"
    return "an object"


def _short(value) -> str:
    if value is None or isinstance(value, (list, dict)):
        return ""
    if isinstance(value, bool):
        shown = "TRUE" if value else "FALSE"
    elif isinstance(value, float) and value == int(value):
        shown = str(int(value))
    elif isinstance(value, str):
        shown = "'" + value + "'"
    else:
        shown = str(value)
    return f" ({shown})"


def _fmt_vec(values, digits: int) -> str:
    return " ".join("NA" if _missing(item) else _num_exact(item, digits) for item in values)


def compare(x, y, tolerance=None, check_attributes: bool = True, max_diffs: int = 9):
    """Edition 2 compare(). Numbers use the mismatch layout from compare.numeric."""
    if _equal_enough(x, y, tolerance):
        return no_difference()
    left, right = _as_floats(x), _as_floats(y)
    if left is None or right is None:
        return difference(f"Types not compatible: {_friendly(x)} is not {_friendly(y)}")
    if len(left) != len(right):
        return difference(f"Lengths differ: {len(left)} is not {len(right)}")
    tol = TOLERANCE if tolerance is None else tolerance
    flags = []
    for a, b in zip(left, right):
        if _missing(a) and _missing(b):
            flags.append(False)
        elif _missing(a) or _missing(b):
            flags.append(True)
        else:
            flags.append(not (a == b or abs(a - b) < tol))
    if not any(flags):
        return no_difference()
    idxs = [i + 1 for i, flag in enumerate(flags) if flag]
    n_diff = len(idxs)
    summary = f"{n_diff}/{len(flags)} mismatches"
    if n_diff > 1:
        mu = sum(abs(left[i - 1] - right[i - 1]) for i in idxs) / n_diff
        summary += f" (average diff: {mu:.3g})"
    show = idxs[:max_diffs]
    lines = []
    for i in show:
        a, b = left[i - 1], right[i - 1]
        lines.append(f"[{i}] {_plain(a)} - {_plain(b)} == {_plain(a - b)}")
    if n_diff > len(show):
        lines.append("...")
    return difference(summary + "\n" + "\n".join(lines))


def _plain(value: float) -> str:
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.3g}"


def _equal_enough(x, y, tolerance) -> bool:
    if x == y and type(x) is type(y):
        return True
    left, right = _as_floats(x), _as_floats(y)
    if left is None or right is None:
        return False
    tol = TOLERANCE if tolerance is None else tolerance
    return num_equal(left, right, tol)


def compare_file_text(old, new) -> bool:
    return _read(old) == _read(new)


def compare_file_binary(old, new) -> bool:
    return open(old, "rb").read() == open(new, "rb").read()


def _read(path: str) -> str:
    return open(path, encoding="utf-8", errors="replace").read()
