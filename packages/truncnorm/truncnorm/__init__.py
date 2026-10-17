"""Truncated normal density, cdf, quantile, draws, mean, and variance.

The formulas follow truncnorm 1.0-9. Ordinary normal probabilities use
extraDistr, which is math.erf. The log cdf inside the mean uses SciPy,
because R's log.p path does not underflow the way log(erf) does. Draws
use extraDistr's generators on boot's Mersenne-Twister.
"""

from __future__ import annotations

import math
import sys

from extradistr._rng import exp_rand, norm_rand, qnorm, runif
from extradistr._special import dnorm, pnorm
from scipy.stats import norm

_EPS = sys.float_info.epsilon
_LOG2 = math.log(2.0)
_INV_SQRT_2PI = 0.39894228040143267794
_T1 = 0.15
_T2 = 2.18
_T3 = 0.725
_T4 = 0.45
_NEGINF = float("-inf")
_POSINF = float("inf")


def _pnorm_log(x, mean=0.0, sd=1.0, lower_tail=True):
    z = (x - mean) / sd
    if lower_tail:
        return float(norm.logcdf(z))
    return float(norm.logsf(z))


def _log1mexp(x):
    """log(1 - exp(x)) for x <= 0. R's R_Log1_Exp."""
    if x == 0.0:
        return _NEGINF
    if x > -_LOG2:
        return math.log(-math.expm1(x))
    return math.log1p(-math.exp(x))


def _logspace_sub(logx, logy):
    return logx + _log1mexp(logy - logx)


def _numeric(x):
    if x is None:
        return []
    if isinstance(x, bool):
        return [float(x)]
    if isinstance(x, (int, float)):
        return [float(x)]
    return [float("-inf") if item == _NEGINF else float(item) for item in x]


def _rows(*vectors):
    lengths = [len(vector) for vector in vectors]
    if not lengths or min(lengths) == 0:
        return None
    width = max(lengths)
    return [tuple(vector[i % len(vector)] for vector in vectors) for i in range(width)]


def _finite(x):
    return math.isfinite(x)


def _e_left(a, mean, sd):
    alpha = (a - mean) / sd
    phi_a = dnorm(alpha, 0.0, 1.0, log=True)
    phi = _pnorm_log(alpha, 0.0, 1.0, lower_tail=False)
    return mean + sd * math.exp(phi_a - phi)


def _e_right(b, mean, sd):
    beta = (b - mean) / sd
    phi_b = dnorm(beta, 0.0, 1.0, log=True)
    phi = _pnorm_log(beta, 0.0, 1.0, lower_tail=True)
    return mean + sd * -math.exp(phi_b - phi)


def _e_both(a, b, mean, sd):
    if b < mean - 6.0 * sd or a > mean + 6.0 * sd:
        return (a + b) / 2.0
    alpha = (a - mean) / sd
    beta = (b - mean) / sd
    phi_a = dnorm(alpha, 0.0, 1.0, log=True)
    phi_alpha = _pnorm_log(alpha, 0.0, 1.0, lower_tail=True)
    phi_b = dnorm(beta, 0.0, 1.0, log=True)
    phi_beta = _pnorm_log(beta, 0.0, 1.0, lower_tail=True)
    if phi_b < phi_a:
        delta_phi = _logspace_sub(phi_a, phi_b)
    else:
        sd = -sd
        delta_phi = _logspace_sub(phi_b, phi_a)
    if phi_beta > phi_alpha:
        sd = -sd
        delta_phi_cdf = _logspace_sub(phi_beta, phi_alpha)
    else:
        delta_phi_cdf = _logspace_sub(phi_alpha, phi_beta)
    return mean + sd * -math.exp(delta_phi - delta_phi_cdf)


def _v_left(a, mean, sd):
    alpha = (a - mean) / sd
    phi_a = dnorm(alpha, 0.0, 1.0, log=False)
    phi = pnorm(alpha, 0.0, 1.0, lower_tail=True, log_p=False)
    lam = phi_a / (1.0 - phi)
    return sd * sd * (1.0 - lam * (lam - alpha))


def _v_right(b, mean, sd):
    return _v_left(-b, -mean, sd)


def _v_both(a, b, mean, sd):
    if b < mean - 6.0 * sd or a > mean + 6.0 * sd:
        return (b - a) * (b - a) / 12.0
    variance = sd * sd
    pi1 = pnorm(a, mean, sd, lower_tail=True, log_p=False)
    pi2 = pnorm(b, mean, sd, lower_tail=True, log_p=False) - pi1
    pi3 = pnorm(b, mean, sd, lower_tail=False, log_p=False)
    e1 = _e_right(a, mean, sd)
    e2 = _e_both(a, b, mean, sd)
    e3 = _e_left(b, mean, sd)
    v1 = _v_right(a, mean, sd)
    v3 = _v_left(b, mean, sd)
    c1 = pi1 * (v1 + (e1 - mean) * (e1 - mean))
    c3 = pi3 * (v3 + (e3 - mean) * (e3 - mean))
    return (variance - c1 - c3) / pi2 - (e2 - mean) * (e2 - mean)


def _cdf(q, a, b, mean, sd):
    if q < a:
        return 0.0
    if q > b:
        return 1.0
    c1 = pnorm(q, mean, sd, lower_tail=True, log_p=False)
    c2 = pnorm(a, mean, sd, lower_tail=True, log_p=False)
    c3 = pnorm(b, mean, sd, lower_tail=True, log_p=False)
    return (c1 - c2) / (c3 - c2)


def _zeroin(ax, bx, fa, fb, func):
    a = ax
    b = bx
    c = a
    fc = fa
    tol = 0.0
    maxit = 201
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    while maxit:
        maxit -= 1
        prev_step = b - a
        tol_act = 2 * _EPS * abs(b) + tol / 2
        new_step = (c - b) / 2
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
            if p < (0.75 * cb * q - abs(tol_act * q) / 2) and p < abs(prev_step * q / 2):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = func(b)
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c = a
            fc = fa
    return b


def _expect(a, b, mean, sd):
    if _finite(a) and _finite(b):
        return _e_both(a, b, mean, sd)
    if a == _NEGINF and _finite(b):
        return _e_right(b, mean, sd)
    if _finite(a) and b == _POSINF:
        return _e_left(a, mean, sd)
    if a == _NEGINF and b == _POSINF:
        return mean
    return math.nan


def _variance(a, b, mean, sd):
    if _finite(a) and _finite(b):
        return _v_both(a, b, mean, sd)
    if a == _NEGINF and _finite(b):
        return _v_right(b, mean, sd)
    if _finite(a) and b == _POSINF:
        return _v_left(a, mean, sd)
    if a == _NEGINF and b == _POSINF:
        return sd * sd
    return math.nan


def dtruncnorm(x, a=_NEGINF, b=_POSINF, mean=0, sd=1):
    rows = _rows(_numeric(x), _numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if rows is None:
        return None
    out = []
    for cx, ca, cb, cmean, csd in rows:
        if ca <= cx <= cb:
            c1 = pnorm(ca, cmean, csd, lower_tail=True, log_p=False)
            c2 = pnorm(cb, cmean, csd, lower_tail=True, log_p=False)
            c3 = csd * (c2 - c1)
            c4 = dnorm((cx - cmean) / csd, 0.0, 1.0, log=True)
            if not math.isfinite(math.log(c3)):
                out.append(1.0 / (cb - ca))
            else:
                out.append(math.exp(c4 - math.log(c3)))
        else:
            out.append(0.0)
    return out


def ptruncnorm(q, a=_NEGINF, b=_POSINF, mean=0, sd=1):
    rows = _rows(_numeric(q), _numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if rows is None:
        return None
    return [_cdf(*row) for row in rows]


def qtruncnorm(p, a=_NEGINF, b=_POSINF, mean=0, sd=1):
    rows = _rows(_numeric(p), _numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if rows is None:
        return None
    out = []
    for cp, ca, cb, cmean, csd in rows:
        if cp == 0.0:
            out.append(ca)
        elif cp == 1.0:
            out.append(cb)
        elif cp < 0.0 or cp > 1.0:
            out.append(math.nan)
        elif ca == _NEGINF and cb == _POSINF:
            out.append(qnorm(cp, cmean, csd, lower_tail=True, log_p=False))
        else:
            lower, upper = ca, cb
            if lower == _NEGINF:
                lower = -1.0
                while _cdf(lower, ca, cb, cmean, csd) - cp >= 0:
                    lower *= 2.0
            elif upper == _POSINF:
                upper = 1.0
                while _cdf(upper, ca, cb, cmean, csd) - cp <= 0:
                    upper *= 2.0

            def gap(x, ca=ca, cb=cb, cmean=cmean, csd=csd, cp=cp):
                return _cdf(x, ca, cb, cmean, csd) - cp

            out.append(_zeroin(lower, upper, gap(lower), gap(upper), gap))
    return out


def etruncnorm(a=_NEGINF, b=_POSINF, mean=0, sd=1):
    rows = _rows(_numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if rows is None:
        return None
    return [_expect(*row) for row in rows]


def vtruncnorm(a=_NEGINF, b=_POSINF, mean=0, sd=1):
    rows = _rows(_numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if rows is None:
        return None
    return [_variance(*row) for row in rows]


def _ers_a_inf(a):
    ainv = 1.0 / a
    while True:
        x = exp_rand() * ainv + a
        rho = math.exp(-0.5 * (x - a) ** 2)
        if runif(0.0, 1.0) <= rho:
            return x


def _ers_a_b(a, b):
    ainv = 1.0 / a
    while True:
        x = exp_rand() * ainv + a
        rho = math.exp(-0.5 * (x - a) ** 2)
        if runif(0.0, 1.0) <= rho and x <= b:
            return x


def _nrs_a_b(a, b):
    x = -sys.float_info.max
    while x < a or x > b:
        x = norm_rand()
    return x


def _nrs_a_inf(a):
    x = -sys.float_info.max
    while x < a:
        x = norm_rand()
    return x


def _hnrs_a_b(a, b):
    x = a - 1.0
    while x < a or x > b:
        x = abs(norm_rand())
    return x


def _urs_a_b(a, b):
    phi_a = dnorm(a, 0.0, 1.0, log=False)
    ub = _INV_SQRT_2PI if a < 0.0 < b else phi_a
    while True:
        x = runif(a, b)
        if runif(0.0, 1.0) * ub <= dnorm(x, 0.0, 1.0, log=False):
            return x


def _r_left(a, mean, sd):
    alpha = (a - mean) / sd
    if alpha < _T4:
        return mean + sd * _nrs_a_inf(alpha)
    return mean + sd * _ers_a_inf(alpha)


def _r_right(b, mean, sd):
    beta = (b - mean) / sd
    return mean - sd * _r_left(-beta, 0.0, 1.0)


def _r_both(a, b, mean, sd):
    alpha = (a - mean) / sd
    beta = (b - mean) / sd
    phi_a = dnorm(alpha, 0.0, 1.0, log=False)
    phi_b = dnorm(beta, 0.0, 1.0, log=False)
    if beta <= alpha:
        return math.nan
    if alpha <= 0.0 <= beta:
        if phi_a <= _T1 or phi_b <= _T1:
            return mean + sd * _nrs_a_b(alpha, beta)
        return mean + sd * _urs_a_b(alpha, beta)
    if alpha > 0.0:
        if phi_a / phi_b <= _T2:
            return mean + sd * _urs_a_b(alpha, beta)
        if alpha < _T3:
            return mean + sd * _hnrs_a_b(alpha, beta)
        return mean + sd * _ers_a_b(alpha, beta)
    if phi_b / phi_a <= _T2:
        return mean - sd * _urs_a_b(-beta, -alpha)
    if beta > -_T3:
        return mean - sd * _hnrs_a_b(-beta, -alpha)
    return mean - sd * _ers_a_b(-beta, -alpha)


def _rnorm(mean, sd):
    if math.isnan(mean) or not math.isfinite(sd) or sd < 0.0:
        return math.nan
    if sd == 0.0 or not math.isfinite(mean):
        return mean
    return mean + sd * norm_rand()


def _one_draw(a, b, mean, sd):
    if _finite(a) and _finite(b):
        return _r_both(a, b, mean, sd)
    if a == _NEGINF and _finite(b):
        return _r_right(b, mean, sd)
    if _finite(a) and b == _POSINF:
        return _r_left(a, mean, sd)
    if a == _NEGINF and b == _POSINF:
        return _rnorm(mean, sd)
    return math.nan


def rtruncnorm(n, a=_NEGINF, b=_POSINF, mean=0, sd=1):
    bounds = (_numeric(a), _numeric(b), _numeric(mean), _numeric(sd))
    if min(len(vector) for vector in bounds) == 0:
        raise ValueError("length of a, b, mean, and sd must be positive")
    if isinstance(n, (list, tuple)):
        if len(n) > 1:
            count = len(n)
        elif len(n) == 1 and isinstance(n[0], (int, float)) and not isinstance(n[0], bool):
            count = n[0]
        else:
            raise RuntimeError("non-numeric argument n.")
    elif isinstance(n, bool) or not isinstance(n, (int, float)):
        raise RuntimeError("non-numeric argument n.")
    else:
        count = n
    if isinstance(count, float) and math.isnan(count):
        raise RuntimeError("n is NA - aborting.")
    if count == 0:
        return None
    count = int(count)
    width = max(count, *(len(vector) for vector in bounds))
    return [_one_draw(*(vector[i % len(vector)] for vector in bounds)) for i in range(width)]
