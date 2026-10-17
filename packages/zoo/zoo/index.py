"""Index extraction and replacement.

``index`` reads the index of a zoo series, ``1:NROW`` for a plain array,
and ``seq(tsp[1], tsp[2], by = 1/frequency)`` for a series that carries
``tsp``. ``index<-`` keeps a zooreg frequency only when the new spacing
still divides it. ``time<-`` on a plain zoo does not require the index
to be sorted.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import numpy as np

from zoo.order import ORDER
from zoo.series import Zoo

_MISSING = object()
_EPOCH = dt.date(1970, 1, 1)
_TOLERANCE = math.sqrt(2.220446049250313e-16)
_DBL_DIG = 15
_DBL_MAX_10_EXP = 308
_MAX_DIGITS = _DBL_MAX_10_EXP + _DBL_DIG
_LOG10_2 = math.log10(2.0)


def index(x: Any, **kwargs: Any) -> Any:
    """Extract the index. A zoo series returns its index attribute."""
    del kwargs
    if isinstance(x, Zoo):
        return _copy_index(x.index)
    tsp = _tsp(x)
    if tsp is not None:
        start, end, frequency = tsp
        return r_seq(start, end, 1.0 / float(frequency))
    return index_default(x)


def index_default(x: Any, **kwargs: Any) -> np.ndarray:
    """``seq_len(NROW(x))``, one-based."""
    del kwargs
    return np.arange(1, _nrow(x) + 1, dtype=int)


def index_set(x: Any, value: Any) -> Zoo:
    """Replace the index. A zooreg may lose its frequency."""
    if not isinstance(x, Zoo):
        raise ValueError("no applicable method for 'index<-'")
    if _is_zooreg(x):
        return _set_zooreg(x, value, "length of index vectors does not match")
    return _set_zoo(x, value, "length of index vectors does not match", sorted_index=True)


def time_set(x: Any, value: Any) -> Zoo:
    """Replace the index through ``time<-``.

    A plain zoo does not check the order. A zooreg uses the same
    replacement as ``index<-``.
    """
    if not isinstance(x, Zoo):
        raise ValueError("no applicable method for 'time<-'")
    if _is_zooreg(x):
        return _set_zooreg(x, value, "length of index vectors does not match")
    return _set_zoo(x, value, "length of time vectors does not match", sorted_index=False)


def _set_zoo(x: Zoo, value: Any, length_message: str, sorted_index: bool) -> Zoo:
    if _index_length(x.index) != _index_length(value):
        raise ValueError(length_message)
    if sorted_index and list(ORDER(value)) != list(range(1, _index_length(value) + 1)):
        raise ValueError("new index needs to be sorted")
    return _clone(x, index=_copy_index(value))


def _set_zooreg(x: Zoo, value: Any, length_message: str) -> Zoo:
    if _index_length(x.index) != _index_length(value):
        raise ValueError(length_message)
    if list(ORDER(value)) != list(range(1, _index_length(value) + 1)):
        raise ValueError("new index needs to be sorted")
    frequency = x.frequency
    regular = True
    ok = _frequency_still_fits(value, frequency)
    if not ok:
        frequency = None
        regular = False
    return _clone(x, index=_copy_index(value), frequency=frequency, regular=regular)


def _frequency_still_fits(value: Any, frequency: Any) -> bool:
    if frequency is None:
        return False
    try:
        delta = numeric_diff(value)
    except (TypeError, ValueError):
        return False
    if len(delta) < 1 or any(_is_na_num(item) for item in delta):
        return False
    smallest = min(delta)
    if smallest == 0.0 or not math.isfinite(smallest):
        return False
    scaled = [item / smallest for item in delta]
    if not all_equal_true(scaled, r_round_values(scaled)):
        return False
    implied = 1.0 / smallest
    if implied > 1.0 and all_equal_true(implied, r_round(implied)):
        implied = r_round(implied)
    return all_equal_true(r_mod(float(frequency), implied), 0.0)


def _is_zooreg(x: Zoo) -> bool:
    return bool(x.regular) or x.frequency is not None


def _clone(x: Zoo, data: Any = None, index: Any = None, frequency: Any = _MISSING, regular: Any = _MISSING) -> Zoo:
    if data is None:
        data = np.array(x.data, copy=True, order="F")
    if index is None:
        index = _copy_index(x.index)
    if frequency is _MISSING:
        frequency = x.frequency
    if regular is _MISSING:
        regular = x.regular
    return Zoo(data, index, frequency=frequency, regular=bool(regular))


def _copy_index(index: Any) -> Any:
    if isinstance(index, np.ndarray):
        return np.array(index, copy=True)
    if isinstance(index, (list, tuple)):
        return list(index)
    return index


def _index_length(index: Any) -> int:
    if isinstance(index, np.ndarray):
        if index.ndim == 0:
            return 1
        return int(index.shape[0]) if index.ndim > 1 else int(index.size)
    if isinstance(index, (list, tuple, range)):
        return len(index)
    return 1


def _nrow(x: Any) -> int:
    if isinstance(x, Zoo):
        return _index_length(x.index)
    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            return 1
        return int(x.shape[0])
    if isinstance(x, str):
        return 1
    if isinstance(x, (list, tuple, range)):
        return len(x)
    return 1


def _tsp(x: Any) -> tuple[float, float, float] | None:
    tsp = getattr(x, "tsp", None)
    if tsp is None or isinstance(x, Zoo):
        return None
    try:
        start, end, frequency = tsp
    except (TypeError, ValueError):
        return None
    return float(start), float(end), float(frequency)


def r_seq(start: float, end: float, by: float) -> np.ndarray:
    """``seq(from, to, by)`` for a positive or negative step."""
    start = float(start)
    end = float(end)
    by = float(by)
    if by == 0.0:
        raise ValueError("invalid '(to - from)/by'")
    count = int(math.floor((end - start) / by + 1e-10))
    if count < 0:
        return np.array([start], dtype=float)
    return start + np.arange(count + 1, dtype=float) * by


def numeric_values(value: Any) -> list[float]:
    if isinstance(value, np.ndarray):
        items = list(np.ravel(value, order="F"))
    elif isinstance(value, (list, tuple, range)):
        items = list(value)
    else:
        items = [value]
    return [_as_float(item) for item in items]


def numeric_diff(value: Any) -> list[float]:
    numbers = numeric_values(value)
    return [numbers[i + 1] - numbers[i] for i in range(len(numbers) - 1)]


def _as_float(value: Any) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, dt.datetime):
        return float(value.timestamp())
    if isinstance(value, dt.date):
        return float((value - _EPOCH).days)
    if isinstance(value, (bool, np.bool_)):
        return float(bool(value))
    number = float(value)
    if isinstance(value, (float, np.floating)) and math.isnan(number):
        return float("nan")
    if number == 0.0:
        return 0.0
    return number


def _is_na_num(value: Any) -> bool:
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return value is None


def r_round(x: Any, digits: Any = 0) -> Any:
    """R ``round`` for one real, following ``fround``."""
    if x is None:
        return None
    x = float(x)
    digits = float(digits)
    if math.isnan(x) or math.isnan(digits):
        return x + digits
    if math.isinf(x):
        return x
    if digits > _MAX_DIGITS or x == 0.0:
        return math.copysign(0.0, x) if x == 0.0 else x
    if digits < -_DBL_MAX_10_EXP:
        return 0.0
    if digits == 0.0:
        return _nearbyint(x)
    dig = int(math.floor(digits + 0.5))
    sign = -1.0 if x < 0.0 else 1.0
    magnitude = abs(x)
    log10x = _LOG10_2 * (0.5 + _logb(magnitude))
    if log10x + dig > _DBL_DIG:
        return sign * magnitude
    if dig <= _DBL_MAX_10_EXP:
        pow10 = 10.0 ** dig
        scaled = magnitude * pow10
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10
        up = math.ceil(scaled) / pow10
    else:
        extra = dig - _DBL_MAX_10_EXP
        pow10 = 10.0 ** _DBL_MAX_10_EXP
        finer = 10.0 ** extra
        scaled = (magnitude * pow10) * finer
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10 / finer
        up = math.ceil(scaled) / pow10 / finer
    distance_up = up - magnitude
    distance_down = magnitude - down
    odd = math.fmod(down_scaled, 2.0) == 1.0
    choose_up = distance_up < distance_down or (odd and distance_up == distance_down)
    return sign * (up if choose_up else down)


def _logb(x: float) -> float:
    _mantissa, exponent = math.frexp(x)
    return float(exponent - 1)


def _nearbyint(x: float) -> float:
    if math.isnan(x) or math.isinf(x) or x == 0.0:
        return math.copysign(0.0, x) if x == 0.0 else x
    magnitude = abs(x)
    down = math.floor(magnitude)
    fraction = magnitude - down
    if fraction > 0.5:
        rounded = down + 1.0
    elif fraction < 0.5:
        rounded = down
    elif math.fmod(down, 2.0) == 0.0:
        rounded = down
    else:
        rounded = down + 1.0
    if rounded == 0.0:
        return math.copysign(0.0, x)
    return math.copysign(rounded, x)


def r_round_values(values: Any, digits: Any = 0) -> list[Any]:
    return [r_round(value, digits) for value in list(values)]


def all_equal(target: Any, current: Any, tolerance: float | None = None) -> bool | str:
    """R ``all.equal`` for plain numeric values. ``TRUE`` or a message."""
    if tolerance is None:
        tolerance = _TOLERANCE
    if np.ndim(target) == 0 and not isinstance(target, (list, tuple, np.ndarray)):
        target = [target]
    if np.ndim(current) == 0 and not isinstance(current, (list, tuple, np.ndarray)):
        current = [current]
    left = [None if item is None else float(item) for item in list(target)]
    right = [None if item is None else float(item) for item in list(current)]
    if len(left) != len(right):
        return f"Numeric: lengths ({len(left)}, {len(right)}) differ"
    left_na = [_is_na_num(item) for item in left]
    right_na = [_is_na_num(item) for item in right]
    if left_na != right_na:
        return "is.na mismatch"
    kept_left: list[float] = []
    kept_right: list[float] = []
    for a, b, missing in zip(left, right, left_na):
        if missing or a == b:
            continue
        kept_left.append(float(a))
        kept_right.append(float(b))
    if not kept_left:
        return True
    count = len(kept_left)
    difference = sum(abs(a - b) for a, b in zip(kept_left, kept_right)) / count
    scale = sum(abs(a) for a in kept_left) / count
    if math.isfinite(scale) and scale > tolerance:
        difference = difference / scale
    if math.isnan(difference) or difference > tolerance:
        return f"Mean difference: {difference}"
    return True


def all_equal_true(target: Any, current: Any, tolerance: float | None = None) -> bool:
    """``identical(all.equal(target, current), TRUE)``."""
    return all_equal(target, current, tolerance) is True


def r_mod(left: float, right: float) -> float:
    """R ``%%`` for finite doubles."""
    if right == 0.0 or not math.isfinite(left) or not math.isfinite(right):
        return float("nan")
    return left - right * math.floor(left / right)


def as_character_double(value: Any) -> str:
    """R ``as.character`` for one double.

    Fifteen significant digits. Scientific notation is used when it is
    shorter. A tie keeps the fixed form. The exponent has a sign and
    two digits.
    """
    if value is None:
        return "NA"
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0.0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed
