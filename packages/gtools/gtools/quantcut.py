"""Factor bins from sample quantiles (gtools 3.9.5 ``quantcut``)."""

from __future__ import annotations

import math
import re
import warnings

import numpy as np

__all__ = ["quantcut", "Quantcut"]

_EPS = np.finfo(float).eps
_INT_MAX = 2147483647
_CUT_FORMALS = (
    "breaks",
    "labels",
    "include.lowest",
    "right",
    "dig.lab",
    "ordered_result",
)
_FORMAL_ALIASES = {"dig_lab": "dig.lab"}


class Quantcut:
    """Factor-like result: interval label per element, ordered ``levels``."""

    __slots__ = ("labels", "levels", "ordered")

    def __init__(self, labels, levels, ordered=False):
        self.labels = list(labels)
        self.levels = list(levels)
        self.ordered = bool(ordered)

    def __iter__(self):
        return iter(self.labels)

    def __len__(self):
        return len(self.labels)

    def __repr__(self):
        shown = [label if label is not None else "NA" for label in self.labels]
        body = " ".join(shown)
        levels = " ".join(self.levels)
        if self.ordered and len(self.levels) > 1:
            levels = " < ".join(self.levels)
        return f"{body}\nLevels: {levels}"


def quantcut(x, q=4, na_rm=True, **kwargs):
    """Bin ``x`` using ``quantile`` breaks and ``cut``-style interval labels."""
    values = _as_numeric(x)
    probs = _normalize_q(q)
    quant = _quantile(values, probs, na_rm=na_rm)
    if any(_duplicated(quant)):
        return _quantcut_duplicated(values, quant, na_rm, kwargs)
    return _bind_cut(values, quant, kwargs)


def _normalize_q(q):
    if isinstance(q, (list, tuple)):
        if len(q) == 1:
            count = _scalar_q(q[0])
            return _seq_length_out(0.0, 1.0, count + 1)
        return [float(p) for p in q]
    array = np.asarray(q)
    if array.ndim == 0 or array.size == 1:
        count = _scalar_q(array.reshape(()).item())
        return _seq_length_out(0.0, 1.0, count + 1)
    return [float(p) for p in array.reshape(-1)]


def _scalar_q(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("invalid number of quantile groups")
    return int(math.trunc(number))


def _quantcut_duplicated(values, quant, na_rm, kwargs):
    dups = _duplicated(quant)
    dup_values = {value for value, flag in zip(quant, dups, strict=True) if flag}
    flag = [value in dup_values if not _is_missing(value) else False for value in values]
    retval = [
        f"[{_r_as_character(value)}]" if hit else None for value, hit in zip(values, flag, strict=True)
    ]
    uniqs = _unique_preserve(quant)
    newquant = [_reposition(values, cut, na_rm) for cut in uniqs]
    non_flag_indices = [index for index, hit in enumerate(flag) if not hit]
    if non_flag_indices:
        sub_values = [values[index] for index in non_flag_indices]
        cut_labels = _cut_labels(sub_values, newquant, kwargs)
        for index, label in zip(non_flag_indices, cut_labels, strict=True):
            retval[index] = label
    order = sorted(range(len(values)), key=lambda index: (math.inf if _is_missing(values[index]) else values[index]))
    levs = _unique_preserve([retval[index] for index in order if retval[index] is not None])
    pairs = _mkpairs(levs)
    closed_lower = [False] * len(levs)
    closed_upper = [True] * len(levs)
    if levs:
        closed_lower[0] = True
    for index in range(1, len(levs)):
        if pairs[0][index] == pairs[0][index - 1] and pairs[0][index] == pairs[1][index - 1]:
            closed_lower[index] = False
    for index in range(len(levs) - 1):
        if pairs[1][index] == pairs[0][index + 1] and pairs[1][index] == pairs[1][index + 1]:
            closed_upper[index] = False
    new_levs = []
    for index, level in enumerate(levs):
        lower = pairs[0][index]
        upper = pairs[1][index]
        if lower == upper:
            new_levs.append(lower)
        else:
            left = "[" if closed_lower[index] else "("
            right = "]" if closed_upper[index] else ")"
            new_levs.append(f"{left}{lower},{upper}{right}")
    mapping = dict(zip(levs, new_levs, strict=True))
    return Quantcut([mapping.get(label, label) if label is not None else None for label in retval], new_levs)


def _reposition(values, cut, na_rm):
    flags = [value >= cut if not _is_missing(value) else False for value in values]
    if na_rm:
        count = sum(1 for hit in flags if hit)
    else:
        count = sum(1 for hit, value in zip(flags, values, strict=True) if hit and not _is_missing(value))
    if count == 0:
        return cut
    candidates = [value for value, hit in zip(values, flags, strict=True) if hit and (na_rm or not _is_missing(value))]
    return min(candidates)


def _mkpairs(levels):
    lowers = []
    uppers = []
    pattern = re.compile(r"[^0-9+.\-]+")
    for level in levels:
        parts = [part for part in pattern.split(level) if part != ""]
        if len(parts) == 1:
            lowers.append(parts[0])
            uppers.append(parts[0])
        else:
            lowers.append(parts[0])
            uppers.append(parts[1])
    return [lowers, uppers]


def _cut_labels(values, breaks, kwargs):
    bound = _bind_cut_formals(breaks, kwargs)
    result = _cut(
        values,
        bound["breaks"],
        labels=bound["labels"],
        include_lowest=bound["include.lowest"],
        right=bound["right"],
        dig_lab=bound["dig.lab"],
        ordered_result=bound["ordered_result"],
    )
    if isinstance(result, Quantcut):
        return result.labels
    return result


def _bind_cut(values, breaks, kwargs):
    bound = _bind_cut_formals(breaks, kwargs)
    return _cut(
        values,
        bound["breaks"],
        labels=bound["labels"],
        include_lowest=bound["include.lowest"],
        right=bound["right"],
        dig_lab=bound["dig.lab"],
        ordered_result=bound["ordered_result"],
    )


def _bind_cut_formals(computed, kwargs):
    bound = {}

    def assign(formal, value):
        if formal in bound:
            raise ValueError(f'formal argument "{formal}" matched by multiple actual arguments')
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
    codes_only = _is_false_label(labels)
    if codes_only:
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
    labels_out = [None if code is None else level_names[code - 1] for code in codes]
    return Quantcut(labels_out, level_names, ordered_result)


def _quantile(values, probs, na_rm):
    if na_rm:
        clean = [value for value in values if not _is_missing(value)]
    else:
        if any(_is_missing(value) for value in values):
            return [float("nan")] * len(probs)
        clean = list(values)
    if not clean:
        return [float("nan")] * len(probs)
    ordered = sorted(clean)
    n = len(ordered)
    return [_type7(ordered, n, prob) for prob in probs]


def _type7(ordered, n, prob):
    index = 1.0 + max(n - 1, 0) * prob
    lo = math.floor(index)
    hi = math.ceil(index)
    left = ordered[lo - 1]
    if index <= lo or hi == lo:
        return float(left)
    right = ordered[hi - 1]
    if left == right:
        return float(left)
    weight = index - lo
    return (1.0 - weight) * left + weight * right


def _duplicated(values):
    seen = set()
    flags = []
    for value in values:
        key = value if not _is_missing(value) else object()
        if key in seen:
            flags.append(True)
        else:
            seen.add(key)
            flags.append(False)
    return flags


def _unique_preserve(values):
    seen = set()
    out = []
    for value in values:
        key = value if not _is_missing(value) else object()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _seq_length_out(frm, to, length_out):
    length_out = int(length_out)
    if length_out < 0:
        raise ValueError("'length.out' must be a non-negative number")
    if length_out == 0:
        return []
    if length_out == 1:
        return [float(frm)]
    if length_out == 2:
        return [float(frm), float(to)]
    if frm == to:
        return [float(frm)] * length_out
    n1 = length_out - 1
    delta = to - frm
    step = delta / n1
    middle = [frm + index * step for index in range(1, length_out - 1)]
    return [float(frm), *[float(value) for value in middle], float(to)]


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
        ok = all(chosen[index] != chosen[index - 1] for index in range(1, len(chosen)))
        if ok:
            break
    if not ok:
        return [f"Range_{index}" for index in range(1, len(breaks))]
    left = "(" if right else "["
    close = "]" if right else ")"
    labels = [f"{left}{chosen[index]},{chosen[index + 1]}{close}" for index in range(len(breaks) - 1)]
    if include_lowest and labels:
        if right:
            labels[0] = "[" + labels[0][1:]
        else:
            labels[-1] = labels[-1][:-1] + "]"
    return labels


def _empty_label(right, include_lowest):
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
    return [start + index * step for index in range(count)]


def _format_digits(dig):
    digits = int(dig)
    if digits < 0:
        return 6
    if digits > 50:
        warnings.warn("'digits' reduced to 50", RuntimeWarning, stacklevel=4)
        return 50
    return digits


def _format_c(value, digits):
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


def _r_as_character(value):
    if _is_missing(value):
        return "NA"
    number = float(value)
    if number == 0.0:
        number = 0.0
    if math.isfinite(number) and number == math.trunc(number):
        return "0" if number == 0 else str(int(number))
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, ".15g")


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
        return _r_as_character(number)
    if value is None:
        return "NA"
    return str(value)


def _expand_single_break(values, break_value):
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
    if not math.isfinite(value) or value > _INT_MAX or value < -2147483648:
        return None
    return int(value)


def _range_na(values):
    kept = [value for value in values if not _is_missing(value)]
    if not kept:
        _warn_empty_range()
        return math.inf, -math.inf
    return min(kept), max(kept)


def _warn_empty_range():
    warnings.warn("no non-missing arguments to min; returning Inf", RuntimeWarning, stacklevel=5)
    warnings.warn("no non-missing arguments to max; returning -Inf", RuntimeWarning, stacklevel=5)


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
