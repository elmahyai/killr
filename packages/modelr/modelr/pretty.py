"""R pretty() and the seq() cases seq_range uses.

pretty() covers a range with about ``n`` intervals. The step is 1, 2, or 5
times a power of ten. seq() with ``length.out`` pins both endpoints. seq()
with ``by`` adds the same fuzz R adds before truncating the count.
"""

from __future__ import annotations

import math
import sys

_EPS = sys.float_info.epsilon
_DBL_MIN = sys.float_info.min
_DBL_MAX = sys.float_info.max
_ROUNDING_EPS = 1e-10


def seq_length(from_, to, length_out):
    """seq(from, to, length.out=n) for finite doubles."""
    if isinstance(length_out, bool) or not isinstance(length_out, (int, float)):
        raise ValueError("'length.out' must be a non-negative number")
    if isinstance(length_out, float):
        if not math.isfinite(length_out):
            raise ValueError("'length.out' must be a non-negative number")
        length_out = int(math.ceil(length_out))
    if length_out < 0:
        raise ValueError("'length.out' must be a non-negative number")
    if length_out == 0:
        return []
    if length_out == 1:
        return [float(from_)]
    if length_out == 2:
        return [float(from_), float(to)]
    if from_ == to:
        return [float(from_)] * length_out
    n1 = length_out - 1
    step = (to - from_) / n1
    middle = [from_ + i * step for i in range(1, length_out - 1)]
    return [float(from_), *[float(v) for v in middle], float(to)]


def seq_by(from_, to, by):
    """seq(from, to, by=by) for finite doubles."""
    if by == 0 and to - from_ == 0:
        return [float(from_)]
    span = to - from_
    if span == 0 and to == 0:
        return [float(to)]
    finite = math.isfinite(span)
    count = span / by if finite else to / by - from_ / by
    if not math.isfinite(count):
        raise ValueError("invalid '(to - from)/by'")
    if count < 0:
        raise ValueError("wrong sign in 'by' argument")
    if count > 2**31 - 1:
        raise ValueError("'by' argument is much too small")
    if finite and abs(span) / max(abs(to), abs(from_)) < 100 * _EPS:
        return [float(from_)]
    n = int(count + 1e-10)
    values = [from_ + i * by for i in range(n + 1)]
    if by > 0:
        values = [min(v, to) for v in values]
    else:
        values = [max(v, to) for v in values]
    return [float(v) for v in values]


def pretty(x, n=5, min_n=None, shrink_sml=0.75, high_u_bias=1.5, u5_bias=None, eps_correct=0, f_min=2**-20):
    """Equally spaced pretty breaks covering the finite values of ``x``."""
    finite = [float(v) for v in x if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not finite:
        return []
    if min_n is None:
        min_n = int(n) // 3
    if u5_bias is None:
        u5_bias = 0.5 + 1.5 * high_u_bias
    lo, up, ndiv, _unit = _r_pretty(
        min(finite),
        max(finite),
        int(n),
        int(min_n),
        float(shrink_sml),
        (float(high_u_bias), float(u5_bias), float(f_min)),
        int(eps_correct),
        True,
    )
    breaks = seq_length(lo, up, ndiv + 1)
    if not eps_correct and ndiv:
        delta = abs(up - lo) / ndiv
        breaks = [0.0 if abs(v) < 1e-14 * delta else v for v in breaks]
    return breaks


def _r_pretty(lo, up, ndiv, min_n, shrink_sml, high_u_fact, eps_correction, return_bounds):
    h, h5, f_min = high_u_fact
    lo_in = lo
    up_in = up
    span = up_in - lo_in
    if span == 0 and up_in == 0:
        cell = 1.0
        small = True
    else:
        cell = max(abs(lo_in), abs(up_in))
        unit_bound = 1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5)
        unit_bound = (1 + unit_bound) * max(1, ndiv) * _EPS
        small = span < cell * unit_bound * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = span
        if math.isfinite(span):
            if ndiv > 1:
                cell /= ndiv
        elif ndiv >= 2:
            cell = up_in / ndiv - lo_in / ndiv
    smallest = f_min * _DBL_MIN
    if smallest == 0:
        smallest = _DBL_MIN
    if cell < smallest:
        cell = smallest
    elif cell > _DBL_MAX / 1.25:
        cell = _DBL_MAX / 1.25
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    candidate = 2 * base
    if candidate - cell < h * (cell - unit):
        unit = candidate
        candidate = 5 * base
        if candidate - cell < h5 * (cell - unit):
            unit = candidate
            candidate = 10 * base
            if candidate - cell < h * (cell - unit):
                unit = candidate
    ns = math.floor(lo_in / unit + _ROUNDING_EPS)
    nu = math.ceil(up_in / unit - _ROUNDING_EPS)
    if eps_correction and (eps_correction > 1 or not small):
        lo = lo * (1 - _EPS) if lo_in != 0 else -_DBL_MIN
        up = up * (1 + _EPS) if up_in != 0 else _DBL_MIN
    while ns * unit > lo + _ROUNDING_EPS * unit:
        ns -= 1
    while not math.isfinite(ns * unit):
        ns += 1
    while nu * unit < up - _ROUNDING_EPS * unit:
        nu += 1
    while not math.isfinite(nu * unit):
        nu -= 1
    intervals = int(0.5 + nu - ns)
    if intervals < min_n:
        extra = min_n - intervals
        if lo_in == 0 and ns == 0 and up_in != 0:
            nu += extra
        elif up_in == 0 and nu == 0 and lo_in != 0:
            ns -= extra
        elif ns >= 0:
            nu += extra // 2
            ns -= extra // 2 + extra % 2
        else:
            ns -= extra // 2
            nu += extra // 2 + extra % 2
        ndiv = min_n
    else:
        ndiv = intervals
    if return_bounds:
        if ns * unit < lo:
            lo = ns * unit
        if nu * unit > up:
            up = nu * unit
    else:
        lo = ns
        up = nu
    return lo, up, ndiv, unit
