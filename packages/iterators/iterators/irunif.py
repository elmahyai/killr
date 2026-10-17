"""irunif from iterators 1.0.14.

``irunif`` is ``makeIwrapper("runif")``. Each step evaluates ``runif`` with the
arguments supplied in the dots. ``count`` is matched by its full name, because
it sits after the dots. When ``count`` is supplied it has to be one number, and
each step subtracts one before the draw. A missing ``count`` does not stop.

The draws follow R's default Mersenne-Twister. ``set_seed`` matches
``set.seed`` for that generator.
"""

from __future__ import annotations

import math
import re
import warnings

import numpy as np

from iterators.core import Iter, IteratorError
from iterators.core import iter as r_iter


_MISSING = object()
_R_XLEN_T_MAX = 4503599627370496
_FORMALS = ("n", "min", "max")
_NUMBER = re.compile(
    r"^[ \t\n\r\f\v]*"
    r"([+-]?(?:(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?|[Ii]nf(?:inity)?|[Nn]a[Nn]))"
    r"[ \t\n\r\f\v]*$"
)

_N = 624
_M = 397
_MATRIX_A = 0x9908B0DF
_UPPER = 0x80000000
_LOWER = 0x7FFFFFFF
_I2_32 = 2.3283064365386963e-10
_I2_32M1 = 2.328306437080797e-10

_mt = [0] * _N
_mti = _N + 1


class _MissingReal:
    """R's NA_real_, kept apart from a plain NaN."""


NA = _MissingReal()


def set_seed(seed):
    """Match R ``set.seed(seed)`` for the Mersenne-Twister."""
    global _mti
    seed = int(seed) & 0xFFFFFFFF
    for _ in range(50):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
    dummy = []
    for _ in range(1 + _N):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
        dummy.append(seed)
    dummy[0] = _N
    for index in range(_N):
        _mt[index] = dummy[index + 1]
    _mti = dummy[0]


def _unif():
    """One draw from R's ``unif_rand``, in (0, 1)."""
    global _mti
    mag01 = (0, _MATRIX_A)
    if _mti >= _N:
        for kk in range(_N - _M):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + _M] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        for kk in range(_N - _M, _N - 1):
            y = (_mt[kk] & _UPPER) | (_mt[kk + 1] & _LOWER)
            _mt[kk] = (_mt[kk + (_M - _N)] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        y = (_mt[_N - 1] & _UPPER) | (_mt[0] & _LOWER)
        _mt[_N - 1] = (_mt[_M - 1] ^ (y >> 1) ^ mag01[y & 1]) & 0xFFFFFFFF
        _mti = 0
    y = _mt[_mti] & 0xFFFFFFFF
    _mti += 1
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    y &= 0xFFFFFFFF
    value = y * _I2_32
    if value <= 0.0:
        return 0.5 * _I2_32M1
    if (1.0 - value) <= 0.0:
        return 1.0 - 0.5 * _I2_32M1
    return value


def _is_bool(value):
    return isinstance(value, (bool, np.bool_))


def _is_real(value):
    return (not _is_bool(value)) and isinstance(value, (int, float, np.integer, np.floating))


def _as_float(value):
    if isinstance(value, np.generic):
        value = value.item()
    return float(value)


def _classify(value):
    """An R vector as ``(kind, elements)``.

    A Python list or tuple is an atomic vector, the way ``c()`` is represented
    beside ``idiv``. ``None`` is ``NULL``. ``bytes`` is a raw vector.
    """
    if value is None:
        return "null", []
    if _is_bool(value):
        return "logical", [bool(value)]
    if _is_real(value):
        return "numeric", [_as_float(value) if isinstance(value, np.generic) else value]
    if isinstance(value, complex):
        return "complex", [value]
    if isinstance(value, str):
        return "character", [value]
    if isinstance(value, (bytes, bytearray)):
        return "raw", list(value)
    if isinstance(value, np.ndarray):
        flat = np.ravel(value, order="F")
        if value.dtype.kind == "b":
            return "logical", [bool(item) for item in flat]
        if value.dtype.kind in "iuf":
            return "numeric", [item.item() for item in flat]
        if value.dtype.kind == "c":
            return "complex", [complex(item) for item in flat]
        if value.dtype.kind in "SU":
            return "character", [str(item) for item in flat]
        return "other", []
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "numeric", []
        if all(_is_bool(item) for item in value):
            return "logical", [bool(item) for item in value]
        if all(isinstance(item, complex) for item in value):
            return "complex", list(value)
        if all(_is_real(item) for item in value):
            return "numeric", [
                _as_float(item) if isinstance(item, np.generic) else item for item in value
            ]
        if all(isinstance(item, str) for item in value):
            return "character", list(value)
        return "other", []
    if isinstance(value, np.generic):
        return _classify(value.item())
    return "other", []


def _real_from_string(text):
    """``asReal`` of one string. The flag is the coercion warning."""
    if text.strip() == "" or text.strip() == "NA":
        return math.nan, False
    matched = _NUMBER.match(text)
    if matched is None:
        return math.nan, True
    return float(matched.group(1)), False


def _length_from_real(number):
    if math.isnan(number) or number < 0 or number > _R_XLEN_T_MAX:
        raise IteratorError("invalid arguments")
    return int(math.trunc(number))


def _result_length(n):
    """``resultLength``: one element is coerced, a longer vector contributes its length."""
    kind, values = _classify(n)
    if kind in ("null", "other"):
        raise IteratorError("invalid arguments")
    if kind == "raw":
        if len(values) == 1:
            raise IteratorError("unimplemented type 'raw' in 'asReal'\n")
        return len(values)
    if len(values) != 1:
        return len(values)
    if kind == "logical":
        return _length_from_real(1.0 if values[0] else 0.0)
    if kind == "numeric":
        return _length_from_real(float(values[0]))
    if kind == "complex":
        real = float(values[0].real)
        imag = float(values[0].imag)
        if math.isnan(real) or math.isnan(imag):
            raise IteratorError("invalid arguments")
        if imag != 0.0:
            warnings.warn(
                "imaginary parts discarded in coercion",
                UserWarning,
                stacklevel=3,
            )
        return _length_from_real(real)
    number, warned = _real_from_string(values[0])
    if warned:
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=3)
    return _length_from_real(number)


def _c_numeric(kind):
    return kind in ("logical", "numeric")


def _finite_float(value):
    if _is_bool(value):
        return 1.0 if value else 0.0
    return float(value)


def _runif_one(left, right):
    if (not math.isfinite(left)) or (not math.isfinite(right)) or right < left:
        return math.nan
    if left == right:
        return left
    draw = _unif()
    while draw <= 0.0 or draw >= 1.0:
        draw = _unif()
    return left + (right - left) * draw


def runif(n, minimum=0, maximum=1):
    """R ``runif(n, min, max)`` under the Mersenne-Twister."""
    min_kind, min_values = _classify(minimum)
    max_kind, max_values = _classify(maximum)
    if not _c_numeric(min_kind) or not _c_numeric(max_kind):
        raise IteratorError("invalid arguments")
    count = _result_length(n)
    if count == 0:
        return []
    if len(min_values) < 1 or len(max_values) < 1:
        warnings.warn("NAs produced", UserWarning, stacklevel=2)
        return [NA] * count
    lows = [_finite_float(value) for value in min_values]
    highs = [_finite_float(value) for value in max_values]
    out = []
    produced_na = False
    low_n = len(lows)
    high_n = len(highs)
    for index in range(count):
        value = _runif_one(lows[index % low_n], highs[index % high_n])
        if isinstance(value, float) and math.isnan(value):
            produced_na = True
        out.append(value)
    if produced_na:
        warnings.warn("NAs produced", UserWarning, stacklevel=2)
    return out


def _deparse(value):
    if _is_bool(value):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        if value.is_integer() and abs(value) < 2**53:
            return str(int(value))
        return format(value, ".15g")
    if isinstance(value, str):
        return '"' + value + '"'
    return str(value)


def _match_runif(pairs):
    """Match a constructed ``runif`` call. Names after the dots were already kept."""
    status = [None] * len(pairs)
    bound = {}
    for index, (name, value) in enumerate(pairs):
        if name in _FORMALS:
            bound[name] = value
            status[index] = "exact"
    for index, (name, value) in enumerate(pairs):
        if name is None or status[index] == "exact":
            continue
        hits = [formal for formal in _FORMALS if formal not in bound and formal.startswith(name)]
        if len(hits) > 1:
            raise IteratorError(f"argument {index + 1} matches multiple formal arguments")
        if len(hits) == 1:
            bound[hits[0]] = value
            status[index] = "partial"
    remaining = [formal for formal in _FORMALS if formal not in bound]
    for index, (name, value) in enumerate(pairs):
        if name is not None:
            continue
        if remaining:
            bound[remaining.pop(0)] = value
            status[index] = "pos"
        else:
            status[index] = "unused"
    unused = []
    for index, (name, value) in enumerate(pairs):
        if status[index] is None:
            unused.append(f"{name} = {_deparse(value)}")
        elif status[index] == "unused":
            unused.append(_deparse(value))
    if unused:
        word = "argument" if len(unused) == 1 else "arguments"
        raise IteratorError(f"unused {word} ({', '.join(unused)})")
    if "n" not in bound:
        raise IteratorError('argument "n" is missing, with no default')
    if "min" not in bound:
        bound["min"] = 0
    if "max" not in bound:
        bound["max"] = 1
    return bound


def _eval_runif(pairs):
    bound = _match_runif(pairs)
    return runif(bound["n"], bound["min"], bound["max"])


def _count_number(count):
    """``is.numeric(count) && length(count) == 1``. Logical values are rejected."""
    if _is_bool(count) or count is None:
        raise IteratorError("count must be a numeric value")
    if _is_real(count):
        return float(count)
    kind, values = _classify(count)
    if kind == "numeric" and len(values) == 1:
        return float(values[0])
    raise IteratorError("count must be a numeric value")


def irunif(*args, count=_MISSING, **kwargs):
    """Draw uniform samples. Stop after ``count`` steps when ``count`` is supplied.

    Arguments other than ``count`` are passed to ``runif``. ``count`` is not
    matched by a prefix and cannot be positional. A count that is not one
    number stops immediately. Each accepted step subtracts one, then draws,
    so a draw that fails still uses up that step.
    """
    limited = count is not _MISSING
    counter = _count_number(count) if limited else None
    pairs = [(None, value) for value in args]
    pairs.extend(kwargs.items())

    def next_el():
        nonlocal counter
        if limited:
            if math.isnan(counter):
                raise IteratorError("missing value where TRUE/FALSE needed")
            if not counter > 0:
                raise IteratorError("StopIteration")
            counter = counter - 1.0
        return _eval_runif(pairs)

    return r_iter(Iter(["abstractiter", "iter"], nextElem=next_el))
