"""Sheather–Jones bandwidth (MASS width.SJ)."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

from mass.errors import MassError
from mass.misc import _vr_den_bin

_DELMAX = 1000.0
_EPSILON = 2.220446049250313e-16


def _vr_phi4_bin(n: int, cnt: np.ndarray, d: float, h: float) -> float:
    nbin = cnt.size
    nn = n
    total = 0.0
    for i in range(nbin):
        delta = i * d / h
        delta *= delta
        if delta >= _DELMAX:
            break
        term = math.exp(-delta / 2.0) * (delta * delta - 6.0 * delta + 3.0)
        total += term * int(cnt[i])
    total = 2.0 * total + nn * 3.0
    return total / (nn * (nn - 1) * (h**5) * math.sqrt(2.0 * math.pi))


def _vr_phi6_bin(n: int, cnt: np.ndarray, d: float, h: float) -> float:
    nbin = cnt.size
    nn = n
    total = 0.0
    for i in range(nbin):
        delta = i * d / h
        delta *= delta
        if delta >= _DELMAX:
            break
        term = math.exp(-delta / 2.0) * (
            delta * delta * delta - 15.0 * delta * delta + 45.0 * delta - 15.0
        )
        total += term * int(cnt[i])
    total = 2.0 * total - 15.0 * nn
    return total / (nn * (nn - 1) * (h**7) * math.sqrt(2.0 * math.pi))


def _uniroot(func, lower: float, upper: float, tol: float, maxit: int = 1000) -> float:
    """R uniroot (Brent zeroin) with endpoint sign check."""
    a = float(lower)
    b = float(upper)
    fa = func(a)
    fb = func(b)
    if fa * fb > 0:
        raise MassError("f() values at end points not of opposite sign")
    c = a
    fc = fa
    remaining = maxit + 1
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    while remaining:
        remaining -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2.0 * _EPSILON * abs(b) + tol / 2.0
        new_step = (c - b) / 2.0
        if abs(new_step) <= tol_act or fb == 0.0:
            return b
        if abs(prev_step) >= tol_act and abs(fa) > abs(fb):
            cb = c - b
            if a == c:
                t1 = fb / fa
                p = cb * t1
                q = 1.0 - t1
            else:
                q = fa / fc
                t1 = fb / fc
                t2 = fb / fa
                p = t2 * (cb * q * (q - t1) - (b - a) * (t1 - 1.0))
                q = (q - 1.0) * (t1 - 1.0) * (t2 - 1.0)
            if p > 0.0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2.0) and p < abs(prev_step * q / 2.0):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = func(b)
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
    return b


def width_sj(
    x,
    nb: int = 1000,
    lower=None,
    upper=None,
    method: Literal["ste", "dpi"] = "ste",
) -> float:
    """Bandwidth by Sheather and Jones pilot estimation of derivatives."""
    if method not in ("ste", "dpi"):
        raise MassError(f"'{method}' is not a valid choice")
    values = np.asarray(x, dtype=float).reshape(-1)
    n = values.size
    if n == 0:
        raise MassError("'x' has length zero")
    d, cnt = _vr_den_bin(values, nb)
    hmax = 1.144 * math.sqrt(float(np.var(values, ddof=1))) * n ** (-0.2)
    if lower is None:
        lo = 0.1 * hmax
    else:
        lo = float(lower)
    if upper is None:
        hi = hmax
    else:
        hi = float(upper)
    quartiles = np.quantile(values, [0.25, 0.75], method="linear")
    scale = min(
        math.sqrt(float(np.var(values, ddof=1))),
        float(quartiles[1] - quartiles[0]) / 1.349,
    )
    a = 1.24 * scale * n ** (-1.0 / 7.0)
    b = 1.23 * scale * n ** (-1.0 / 9.0)
    c1 = 1.0 / (2.0 * math.sqrt(math.pi) * n)

    def sdh(h: float) -> float:
        return _vr_phi4_bin(n, cnt, d, h)

    def tdh(h: float) -> float:
        return _vr_phi6_bin(n, cnt, d, h)

    td = -tdh(b)
    alph2 = 1.357 * (sdh(a) / td) ** (1.0 / 7.0)

    def fsd(h: float) -> float:
        return (c1 / sdh(alph2 * h ** (5.0 / 7.0))) ** 0.2 - h

    if method == "dpi":
        res = (c1 / sdh((2.394 / (n * td)) ** (1.0 / 7.0))) ** 0.2
    else:
        if fsd(lo) * fsd(hi) > 0:
            raise MassError("no solution in the specified range of bandwidths")
        res = _uniroot(fsd, lo, hi, tol=0.1 * lo)
    return 4.0 * res
