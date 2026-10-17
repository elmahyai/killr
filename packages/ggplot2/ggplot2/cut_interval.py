"""Equal-range intervals for a numeric vector.

``n`` groups share one range. ``length`` is the width of each group.
The lowest endpoint is included. Extra arguments are the ones ``cut`` accepts:
``labels``, ``right``, ``dig_lab``, and ``ordered_result``.
"""

from __future__ import annotations

import math
import sys
import warnings

import numpy as np

__all__ = ["cut_interval"]

_EPS = sys.float_info.epsilon
_INT_MAX = 2147483647
_INT_MIN = -2147483648
_CUT_FORMALS = (
    "breaks",
    "labels",
    "include.lowest",
    "right",
    "dig.lab",
    "ordered_result",
)
_FORMAL_ALIASES = {"dig_lab": "dig.lab"}


class CutInterval:
    """Factor returned by :func:`cut_interval`.

    ``codes`` are 1-based bin numbers. A missing code is ``None``.
    ``levels`` are the interval labels, in bin order.
    """

    def __init__(self, codes, levels, ordered=False):
        self.codes = list(codes)
        self.levels = list(levels)
        self.ordered = bool(ordered)

    def __iter__(self):
        for code in self.codes:
            if code is None:
                yield None
            else:
                yield int(code)

    def __len__(self):
        return len(self.codes)

    def __repr__(self):
        shown = []
        for code in self.codes:
            if code is None:
                shown.append("NA")
            else:
                shown.append(self.levels[code - 1])
        body = " ".join(shown)
        levels = " ".join(self.levels)
        if self.ordered and len(self.levels) > 1:
            levels = " < ".join(self.levels)
        return f"{body}\nLevels: {levels}"

    def __str__(self):
        return self.__repr__()


def cut_interval(x, n=None, length=None, **kwargs):
    """Cut ``x`` into equal-range intervals.

    Pass ``n`` or ``length``, not both. The result is a factor whose first
    interval includes the lowest break. ``labels=False`` returns the integer
    codes instead, with ``None`` where R would write ``NA``.
    """
    if (n is not None and length is not None) or (n is None and length is None):
        raise ValueError("Specify exactly one of `n` and `length`.")

    values = _as_numeric(x)
    if length is None:
        length_out = _prepare_length_out(n)
        lo, hi = _range_finite(values)
        computed = _seq_length_out(lo, hi, length_out)
    else:
        lo, hi = _range_finite(values)
        computed = _fullseq((lo, hi), _as_by(length))
    bound = _bind_cut(computed, kwargs)
    return _cut(
        values,
        bound["breaks"],
        labels=bound["labels"],
        include_lowest=bound["include.lowest"],
        right=bound["right"],
        dig_lab=bound["dig.lab"],
        ordered_result=bound["ordered_result"],
    )


def _bind_cut(computed, kwargs):
    """Match ``cut(x, computed, include.lowest=TRUE, ...)`` the way R does."""
    bound = {}

    def assign(formal, value):
        if formal in bound:
            raise ValueError(
                f'formal argument "{formal}" matched by multiple actual arguments'
            )
        bound[formal] = value

    assign("include.lowest", True)
    for key, value in kwargs.items():
        formal = _match_formal(key)
        if formal is None:
            continue
        assign(formal, value)
    for formal in _CUT_FORMALS:
        if formal not in bound:
            bound[formal] = computed
            break
    bound.setdefault("labels", None)
    bound.setdefault("right", True)
    bound.setdefault("dig.lab", 3)
    bound.setdefault("ordered_result", False)
    if "breaks" not in bound:
        raise ValueError('argument "breaks" is missing, with no default')
    return bound


def _match_formal(name):
    name = _FORMAL_ALIASES.get(name, name)
    if name in _CUT_FORMALS:
        return name
    matches = [formal for formal in _CUT_FORMALS if formal.startswith(name) and name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"argument {name!r} matches multiple formal arguments")
    return None


def _cut(values, breaks, labels, include_lowest, right, dig_lab, ordered_result):
    breaks = _as_break_list(breaks)
    if len(breaks) == 1:
        breaks = _expand_single_break(values, breaks[0])
    else:
        breaks = _sort_breaks(breaks)
    if _any_duplicated(breaks):
        raise ValueError("'breaks' are not unique")

    include_lowest = _as_logical(include_lowest, "include.lowest")
    right = _as_logical(right, "right")
    ordered_result = _as_logical(ordered_result, "ordered_result")
    n_intervals = len(breaks) - 1
    codes_only = False
    if _is_false_label(labels):
        codes_only = True
        level_names = None
    elif labels is None:
        level_names = _auto_labels(breaks, right, include_lowest, dig_lab)
    else:
        level_names = _coerce_labels(labels)
        if len(level_names) != n_intervals:
            raise ValueError("number of intervals and length of 'labels' differ")

    codes = [_bincode(value, breaks, right, include_lowest) for value in values]
    if codes_only:
        return codes
    return CutInterval(codes, level_names, ordered_result)


def _expand_single_break(values, break_value):
    """A single break is a requested interval count, not one cut point."""
    if _is_missing(break_value) or not (break_value >= 2):
        raise ValueError("invalid number of intervals")
    nb = _as_r_integer(break_value + 1)
    if nb is None:
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=4)
        raise ValueError("'length.out' must be a non-negative number")
    lo, hi = _range_na(values)
    dx = hi - lo
    if _is_missing(dx):
        raise ValueError("missing value where TRUE/FALSE needed")
    if dx == 0:
        dx = abs(lo) if lo != 0 else 1.0
        return _seq_length_out(lo - dx / 1000.0, hi + dx / 1000.0, nb)
    breaks = _seq_length_out(lo, hi, nb)
    breaks[0] = lo - dx / 1000.0
    breaks[-1] = hi + dx / 1000.0
    return breaks


def _as_r_integer(value):
    if not math.isfinite(value) or value > _INT_MAX or value < _INT_MIN:
        return None
    return int(value)


def _bincode(value, breaks, right, include_lowest):
    if _is_missing(value) or not breaks:
        return None
    lo = 0
    hi = len(breaks) - 1
    opened_on_the_left = not right
    if (
        value < breaks[lo]
        or breaks[hi] < value
        or (value == breaks[lo] and not include_lowest and not opened_on_the_left)
        or (value == breaks[hi] and not include_lowest and opened_on_the_left)
    ):
        return None
    while hi - lo >= 2:
        mid = (hi + lo) // 2
        if value > breaks[mid] or (opened_on_the_left and value == breaks[mid]):
            lo = mid
        else:
            hi = mid
    return lo + 1


def _auto_labels(breaks, right, include_lowest, dig_lab):
    if not breaks:
        return [_empty_label(right, include_lowest)]
    digits = _digit_sequence(dig_lab)
    chosen = None
    ok = False
    for dig in digits:
        chosen = [_format_c(value, _format_digits(dig)) for value in breaks]
        ok = all(chosen[i] != chosen[i - 1] for i in range(1, len(chosen)))
        if ok:
            break
    if not ok:
        return [f"Range_{i}" for i in range(1, len(breaks))]
    left = "(" if right else "["
    close = "]" if right else ")"
    labels = [
        f"{left}{chosen[i]},{chosen[i + 1]}{close}" for i in range(len(breaks) - 1)
    ]
    if include_lowest and labels:
        if right:
            labels[0] = "[" + labels[0][1:]
        else:
            labels[-1] = labels[-1][:-1] + "]"
    return labels


def _empty_label(right, include_lowest):
    # paste0 of empty edges keeps the literal punctuation, so the label is "(,]".
    label = f"{'(' if right else '['},{']' if right else ')'}"
    if include_lowest:
        if right:
            label = "[" + label[1:]
        else:
            label = label[:-1] + "]"
    return label


def _digit_sequence(dig_lab):
    dig = _one_number(dig_lab, "dig.lab")
    if _is_missing(dig):
        raise ValueError("NA/NaN argument")
    end = dig if dig > 12 else 12.0
    if dig == math.trunc(dig) and end == math.trunc(end):
        return list(range(int(dig), int(end) + (1 if end >= dig else -1), 1 if end >= dig else -1))
    return _colon(dig, end)


def _colon(start, end):
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("NA/NaN argument")
    step = 1.0 if end >= start else -1.0
    count = int(abs(end - start) + 1.0 + 1.0e-10)
    return [start + i * step for i in range(count)]


def _format_digits(dig):
    # formatC passes digits through as.integer, which truncates toward zero.
    digits = int(dig)
    if digits < 0:
        return 6
    if digits > 50:
        warnings.warn("'digits' reduced to 50", RuntimeWarning, stacklevel=4)
        return 50
    return digits


def _format_c(value, digits):
    """``formatC(0 + x, digits=digits, width=1)`` for a finite break."""
    value = value + 0.0
    if value == 0:
        value = 0.0
    if _is_missing(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if digits <= 0:
        return format(value, ".1g")
    return format(value, f".{digits}g")


def _is_false_label(labels):
    if isinstance(labels, (bool, np.bool_)):
        return not bool(labels)
    if isinstance(labels, np.ndarray) and labels.shape == () and labels.dtype == bool:
        return not bool(labels.item())
    return False


def _coerce_labels(labels):
    if isinstance(labels, (str, bytes)):
        text = labels.decode() if isinstance(labels, bytes) else labels
        return [text]
    if isinstance(labels, (bool, np.bool_)):
        return ["TRUE" if bool(labels) else "FALSE"]
    if isinstance(labels, np.ndarray) and labels.ndim == 0:
        return [_as_character(labels.item())]
    if isinstance(labels, (list, tuple, np.ndarray, range)):
        return [_as_character(value) for value in labels]
    return [_as_character(labels)]


def _as_character(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return "NaN"
        if math.isinf(number):
            return "Inf" if number > 0 else "-Inf"
        return format(number, ".15g")
    if value is None:
        return "NA"
    return str(value)


def _fullseq(range_pair, size):
    lo, hi = _sort_pair(range_pair[0], range_pair[1])
    zero = _zero_range((lo, hi))
    if zero is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if zero:
        return [lo + size * (-1.0) / 2.0, hi + size * 1.0 / 2.0]
    return _seq_by(_round_any(lo, size, math.floor), _round_any(hi, size, math.ceil), size)


def _round_any(x, accuracy, rounder):
    if _is_missing(x) or _is_missing(accuracy) or accuracy == 0:
        return float("nan")
    quotient = x / accuracy
    if _is_missing(quotient) or math.isinf(quotient):
        return float("nan")
    return rounder(quotient) * accuracy


def _zero_range(pair, tol=None):
    if tol is None:
        tol = 1000.0 * _EPS
    if len(pair) == 1:
        return True
    left, right = pair
    if _is_missing(left) or _is_missing(right):
        return None
    if left == right:
        return True
    if math.isinf(left) or math.isinf(right):
        return False
    scale = min(abs(left), abs(right))
    if scale == 0:
        return False
    return abs((left - right) / scale) < tol


def _prepare_length_out(n):
    values = _as_float_vector(n, "'length.out' must be of length 1")
    if len(values) > 1:
        warnings.warn(
            "first element used of 'length.out' argument",
            RuntimeWarning,
            stacklevel=3,
        )
        values = values[:1]
    total = values[0] + 1.0
    if _is_missing(total):
        raise ValueError("'length.out' must be a non-negative number")
    total = math.ceil(total)
    if not math.isfinite(total) or total < 0:
        raise ValueError("'length.out' must be a non-negative number")
    if total > _INT_MAX:
        raise ValueError("'length.out' must be a non-negative number")
    return int(total)


def _seq_length_out(frm, to, length_out):
    if isinstance(length_out, float):
        if not math.isfinite(length_out) or length_out < 0:
            raise ValueError("'length.out' must be a non-negative number")
        length_out = int(math.ceil(length_out))
    if not math.isfinite(frm):
        raise ValueError("'from' must be a finite number")
    if not math.isfinite(to):
        raise ValueError("'to' must be a finite number")
    if length_out < 0:
        raise ValueError("'length.out' must be a non-negative number")
    if length_out == 0:
        return []
    frm = float(frm)
    to = float(to)
    if length_out == 1:
        return [frm]
    if length_out == 2:
        return [frm, to]
    if frm == to:
        return [frm] * length_out
    n1 = length_out - 1
    delta = to - frm
    if math.isfinite(delta):
        step = delta / n1
        middle = [frm + i * step for i in range(1, length_out - 1)]
        return [frm, *middle, to]
    frm4 = frm / 4.0
    to4 = to / 4.0
    step = (to4 - frm4) / n1
    middle = [frm4 + i * step for i in range(1, length_out - 1)]
    return [value * 4.0 for value in (frm4, *middle, to4)]


def _seq_by(frm, to, by):
    if not math.isfinite(frm):
        raise ValueError("'from' must be a finite number")
    if not math.isfinite(to):
        raise ValueError("'to' must be a finite number")
    if _is_missing(by):
        raise ValueError("invalid '(to - from)/by'")
    delta = to - frm
    if delta == 0 and to == 0:
        return [to]
    finite_delta = math.isfinite(delta)
    if by == 0 and delta == 0:
        return [frm]
    try:
        steps = delta / by if finite_delta else to / by - frm / by
    except ZeroDivisionError:
        steps = float("inf")
    if not math.isfinite(steps):
        if by == 0 and delta == 0:
            return [frm]
        raise ValueError("invalid '(to - from)/by'")
    if steps < 0:
        raise ValueError("wrong sign in 'by' argument")
    if steps > _INT_MAX:
        raise ValueError("'by' argument is much too small")
    if finite_delta and max(abs(to), abs(frm)) != 0:
        if abs(delta) / max(abs(to), abs(frm)) < 100.0 * _EPS:
            return [frm]
    count = int(steps + 1e-10)
    if finite_delta:
        values = [frm + i * by for i in range(count + 1)]
    else:
        values = [(frm / 4.0 + i * (by / 4.0)) * 4.0 for i in range(count + 1)]
    if by > 0:
        return [value if value <= to else to for value in values]
    return [value if value >= to else to for value in values]


def _range_finite(values):
    kept = [value for value in values if math.isfinite(value)]
    if not kept:
        _warn_empty_range()
        return math.inf, -math.inf
    return min(kept), max(kept)


def _range_na(values):
    kept = [value for value in values if not _is_missing(value)]
    if not kept:
        _warn_empty_range()
        return math.inf, -math.inf
    return min(kept), max(kept)


def _warn_empty_range():
    warnings.warn(
        "no non-missing arguments to min; returning Inf",
        RuntimeWarning,
        stacklevel=5,
    )
    warnings.warn(
        "no non-missing arguments to max; returning -Inf",
        RuntimeWarning,
        stacklevel=5,
    )


def _as_by(length):
    values = _as_float_vector(length, "'by' must be of length 1")
    if len(values) != 1:
        raise ValueError("'by' must be of length 1")
    return values[0]


def _one_number(value, name):
    values = _as_float_vector(value, f"'{name}' must be of length 1")
    if len(values) != 1:
        raise ValueError(f"'{name}' must be of length 1")
    return values[0]


def _as_numeric(x):
    if isinstance(x, bool) or x is None:
        raise ValueError("'x' must be numeric")
    if isinstance(x, (str, bytes, dict, complex)):
        raise ValueError("'x' must be numeric")
    if isinstance(x, np.ndarray) and (x.dtype == bool or x.dtype.kind in "cOSU"):
        raise ValueError("'x' must be numeric")
    if isinstance(x, np.ndarray):
        if x.dtype.kind in "iuf":
            if x.ndim == 0:
                return [_one_float(x.item())]
            return [_one_float(value) for value in np.ravel(x, order="F")]
        raise ValueError("'x' must be numeric")
    if isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool):
        return [_one_float(x)]
    if isinstance(x, (list, tuple, range)):
        return [_element_float(value) for value in x]
    if isinstance(x, np.generic) and not isinstance(x, (np.bool_, np.str_)):
        return [_one_float(x)]
    try:
        iterator = iter(x)
    except TypeError as error:
        raise ValueError("'x' must be numeric") from error
    return [_element_float(value) for value in iterator]


def _element_float(value):
    if isinstance(value, (str, bytes, dict, complex)) or isinstance(value, bool):
        raise ValueError("'x' must be numeric")
    return _one_float(value)


def _one_float(value):
    if value is None:
        return float("nan")
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("'x' must be numeric")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    raise ValueError("'x' must be numeric")


def _as_float_vector(value, empty_message):
    if value is None:
        raise ValueError(empty_message)
    if isinstance(value, (str, bytes, dict, complex)):
        raise ValueError("non-numeric argument to binary operator")
    if isinstance(value, (bool, np.bool_)):
        return [float(bool(value))]
    if isinstance(value, (int, float, np.integer, np.floating)):
        return [float(value)]
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return _as_float_vector(value.item(), empty_message)
    if isinstance(value, (list, tuple, range, np.ndarray)):
        if len(value) == 0:
            raise ValueError(empty_message)
        return [_element_float(item) for item in value]
    raise ValueError("non-numeric argument to binary operator")


def _as_break_list(breaks):
    if isinstance(breaks, (list, tuple)):
        return [float(value) for value in breaks]
    if isinstance(breaks, np.ndarray):
        return [float(value) for value in np.ravel(breaks, order="F")]
    return [float(breaks)]


def _as_logical(value, name):
    if isinstance(value, (list, tuple, np.ndarray)) and np.ndim(value) > 0 and len(value) != 1:
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        raise ValueError("the condition has length > 1")
    if isinstance(value, (list, tuple, np.ndarray)) and np.ndim(value) > 0:
        value = value[0]
    if isinstance(value, np.ndarray) and value.ndim == 0:
        value = value.item()
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if _is_missing(number):
            raise ValueError("missing value where TRUE/FALSE needed")
        return number != 0.0
    raise ValueError("missing value where TRUE/FALSE needed")


def _sort_breaks(breaks):
    finite = [value for value in breaks if not _is_missing(value)]
    missing = [value for value in breaks if _is_missing(value)]
    finite.sort()
    return finite + missing


def _sort_pair(left, right):
    if _is_missing(left) or _is_missing(right):
        return left, right
    if left <= right:
        return left, right
    return right, left


def _any_duplicated(breaks):
    seen_missing = False
    seen = []
    for value in breaks:
        if _is_missing(value):
            if seen_missing:
                return True
            seen_missing = True
            continue
        for previous in seen:
            if value == previous:
                return True
        seen.append(value)
    return False


def _is_missing(value):
    return isinstance(value, float) and math.isnan(value)
