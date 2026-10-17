"""Power of Fisher's exact test by simulation.

Translated from statmod 1.5.2 ``power.fisher.test`` in ``R/power.R``.
"""

from __future__ import annotations

import math

from scipy.stats import fisher_exact

from statmod.gauss_quad import _match_arg

_ALTERNATIVES = ("two.sided", "greater", "less")
_SCIPY_ALTERNATIVE = {
    "two.sided": "two-sided",
    "greater": "greater",
    "less": "less",
}


def power_fisher_test(p1, p2, n1, n2, alpha=0.05, nsim=100, alternative="two.sided"):
    """Estimated power of Fisher's exact test for two proportions."""
    alt = _match_arg(alternative, _ALTERNATIVES)
    n1 = int(n1)
    n2 = int(n2)
    nsim = int(nsim)
    alpha = float(alpha)
    p1 = float(p1)
    p2 = float(p2)

    y1 = _rbinom(nsim, n1, p1)
    y2 = _rbinom(nsim, n2, p2)
    reject = 0
    scipy_alt = _SCIPY_ALTERNATIVE[alt]
    for i in range(nsim):
        table = [[y1[i], n1 - y1[i]], [y2[i], n2 - y2[i]]]
        p_value = fisher_exact(table, alternative=scipy_alt)[1]
        if p_value < alpha:
            reject += 1
    return reject / nsim


def set_seed(seed: int) -> None:
    """Match R ``set.seed`` for the default Mersenne-Twister."""
    global _mti
    seed &= 0xFFFFFFFF
    for _ in range(50):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
    dummy = []
    for _ in range(1 + _N):
        seed = (69069 * seed + 1) & 0xFFFFFFFF
        dummy.append(seed)
    dummy[0] = _N
    for i in range(_N):
        _mt[i] = dummy[i + 1]
    _mti = dummy[0]


_N = 624
_M = 397
_MATRIX_A = 0x9908B0DF
_UPPER = 0x80000000
_LOWER = 0x7FFFFFFF
_I2_32 = 2.3283064365386963e-10
_I2_32M1 = 2.328306437080797e-10

_mt = [0] * _N
_mti = _N + 1


def _unif() -> float:
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
    x = y * _I2_32
    if x <= 0.0:
        return 0.5 * _I2_32M1
    if (1.0 - x) <= 0.0:
        return 1.0 - 0.5 * _I2_32M1
    return x


def _rbinom(n, size, prob):
    size = int(size)
    prob = float(prob)
    return [_rbinom_one(size, prob) for _ in range(int(n))]


def _r_pow_di(x, n):
    power = 1.0
    if n:
        if n < 0:
            n = -n
            x = 1.0 / x
        while True:
            if n & 1:
                power *= x
            n >>= 1
            if n:
                x *= x
            else:
                break
    return power


def _rbinom_one(nin, pp):
    if nin == 0 or pp == 0.0:
        return 0
    if pp == 1.0:
        return int(nin)
    n = int(nin)
    p = min(pp, 1.0 - pp)
    q = 1.0 - p
    np_ = n * p
    ratio = p / q
    g = ratio * (n + 1)
    if np_ < 30.0:
        qn = _r_pow_di(q, n)
        ix = 0
        f = qn
        u = _unif()
        while u >= f:
            if ix > 110:
                u = _unif()
                ix = 0
                f = qn
                continue
            u -= f
            ix += 1
            f *= g / ix - ratio
        return (n - ix) if pp > 0.5 else ix
    ffm = np_ + p
    mode = int(ffm)
    fm = float(mode)
    npq = np_ * q
    p1 = int(2.195 * math.sqrt(npq) - 4.6 * q) + 0.5
    xm = fm + 0.5
    xl = xm - p1
    xr = xm + p1
    c = 0.134 + 20.5 / (15.3 + fm)
    al = (ffm - xl) / (ffm - xl * p)
    xll = al * (1.0 + 0.5 * al)
    al = (xr - ffm) / (xr * q)
    xlr = al * (1.0 + 0.5 * al)
    p2 = p1 * (1.0 + c + c)
    p3 = p2 + c / xll
    p4 = p3 + c / xlr
    while True:
        u = _unif() * p4
        v = _unif()
        if u <= p1:
            ix = int(xm - p1 * v + u)
            break
        if u <= p2:
            x = xl + (u - p1) / c
            v = v * c + 1.0 - abs(xm - x) / p1
            if v > 1.0 or v <= 0.0:
                continue
            ix = int(x)
        else:
            if u > p3:
                ix = int(xr - math.log(v) / xlr)
                if ix > n:
                    continue
                v = v * (u - p3) * xlr
            else:
                ix = int(xl + math.log(v) / xll)
                if ix < 0:
                    continue
                v = v * (u - p2) * xll
        k = abs(ix - mode)
        if k <= 20 or k >= npq / 2.0 - 1.0:
            f = 1.0
            if mode < ix:
                for i in range(mode + 1, ix + 1):
                    f *= g / i - ratio
            elif mode > ix:
                for i in range(ix + 1, mode + 1):
                    f /= g / i - ratio
            if v <= f:
                break
        else:
            amaxp = (k / npq) * ((k * (k / 3.0 + 0.625) + 0.1666666666666) / npq + 0.5)
            ynorm = -k * k / (2.0 * npq)
            alv = math.log(v)
            if alv < ynorm - amaxp:
                break
            if alv <= ynorm + amaxp:
                x1 = ix + 1.0
                f1 = fm + 1.0
                z = n + 1.0 - fm
                w = n - ix + 1.0
                z2 = z * z
                x2 = x1 * x1
                f2 = f1 * f1
                w2 = w * w
                stirling = (
                    xm * math.log(f1 / x1)
                    + (n - mode + 0.5) * math.log(z / w)
                    + (ix - mode) * math.log(w * p / (x1 * q))
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / f2) / f2) / f2) / f2) / f1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / z2) / z2) / z2) / z2) / z / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / x2) / x2) / x2) / x2) / x1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / w2) / w2) / w2) / w2) / w / 166320.0
                )
                if alv <= stirling:
                    break
    return (n - ix) if pp > 0.5 else ix
