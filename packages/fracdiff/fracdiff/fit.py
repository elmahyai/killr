"""Haslett-Raftery fractional ARIMA and the periodogram estimators.

The likelihood constant is the literal 2.8378 from the C, not log(2*pi) + 1.
The maximized variance divides by n. The Hessian's trial variances divide by
n - 1.
"""

from __future__ import annotations

import math

import numpy as np

_EPS = 2.220446049250313e-16
_NEG_EPS = 1.1102230246251565e-16
_XMIN = 2.2250738585072014e-308
_XMAX = 1.7976931348623157e308
_EPSPT5 = math.sqrt(_NEG_EPS)
_EPSP25 = math.sqrt(_EPSPT5)
_CC = 0.38196601125011
_LIKE = 2.8378


class Fracdiff:
    """The fracdiff fit. ar and ma are empty when those orders are zero."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        return f"Fracdiff(d={self.d!r}, log_likelihood={self.log_likelihood!r})"

    def __str__(self):
        coefs = _coef(self)
        names = " ".join(coefs)
        values = " ".join(f"{coefs[name]:.6g}" for name in coefs)
        lines = [
            "",
            f"Call:",
            f"  fracdiff(x)",
            "",
            "Coefficients:",
            f"  {names}",
            f"  {values}",
            f"sigma[eps] = {self.sigma}",
        ]
        return "\n".join(lines)


def diffseries(x, d):
    """Fractionally difference x. The series is centered first."""
    values = np.asarray(_vector(x), dtype=float)
    length = len(values)
    if length < 2:
        raise ValueError("length(x) >= 2 is not TRUE")
    centered = values - float(np.mean(values))
    width = nextn(length + length - 1)
    pad = width - length
    k = np.arange(1, length, dtype=float)
    weights = np.cumprod((k - (d + 1.0)) / k)
    kernel = np.concatenate(([1.0], weights, np.zeros(pad)))
    padded = np.concatenate((centered, np.zeros(pad)))
    transformed = np.fft.ifft(np.fft.fft(kernel) * np.fft.fft(padded))
    return np.real(transformed[:length])


def fd_gph(x, bandw_exp=0.5):
    """Geweke-Porter-Hudak regression of the log periodogram."""
    return _periodogram_d(x, bandw_exp, beta=None)


def fd_sperio(x, bandw_exp=0.5, beta=0.9):
    """Smoothed periodogram estimator of d."""
    return _periodogram_d(x, bandw_exp, beta=beta)


def fracdiff_sim(
    n,
    d,
    ar=None,
    ma=None,
    rand_gen=None,
    innov=None,
    n_start=None,
    back_comp=True,
    allow_0_nstart=False,
    start_innov=None,
    mu=0.0,
):
    """Simulate an ARFIMA series. Pass innov to avoid R's random generator."""
    ar = [] if ar is None else [float(value) for value in ar]
    ma = [] if ma is None else [float(value) for value in ma]
    p = len(ar)
    q = len(ma)
    minroots = None
    if p:
        minroots = _min_root(ar)
        if minroots <= 1.0:
            minroots = 1.01
    if n_start is None:
        burn = p + q + (math.ceil(6.0 / math.log(minroots)) if p else 0)
    else:
        burn = int(n_start)
    if burn < p + q and not allow_0_nstart:
        raise ValueError("burn-in 'n.start' must be as long as 'ar + ma'")
    if d < -0.5 or d > 0.5:
        raise ValueError(
            "'d' must be in [-1/2, 1/2].  Consider using cumsum(.) or diff(.)\n"
            " for additional integration or differentiation"
        )
    if innov is None:
        if rand_gen is None:
            raise ValueError("pass innov or rand_gen; the default is R's rnorm")
        innov = [float(value) for value in rand_gen(n + q)]
    else:
        innov = [float(value) for value in innov]
    if start_innov is None:
        if rand_gen is None:
            start = [0.0] * burn
        else:
            start = [float(value) for value in rand_gen(burn)]
    else:
        start = [float(value) for value in start_innov]
        if len(start) < burn:
            raise ValueError(f"'start.innov' is too short: need {burn} points")
    if len(innov) < n + q:
        raise ValueError("'innov' must have length >= n + q")
    y = start[:burn] + innov[: n + q]
    series = _fdsim(n + burn, ar, ma, float(d), float(mu), y)
    start_at = burn - (0 if back_comp else q)
    kept = series[start_at : start_at + n]
    return {
        "series": kept,
        "ar": ar,
        "ma": ma,
        "d": float(d),
        "mu": float(mu),
        "n_start": burn,
    }


def fracdiff(x, nar=0, nma=0, ar=None, ma=None, dtol=None, drange=(0.0, 0.5), h=None, m=100, trace=0):
    """Maximum likelihood ARFIMA fit. nar and nma must be 0 in this translation."""
    if int(nar) != 0 or int(nma) != 0:
        raise NotImplementedError(
            "fracdiff with a positive AR or MA order is still the MINPACK fit"
        )
    values = _vector(x)
    if any(math.isnan(value) for value in values):
        raise ValueError("missing values not allowed in time series")
    n = len(values)
    if dtol is None:
        dtol = _EPS ** 0.25
    tolerance = float(dtol)
    if tolerance > 0.1:
        tolerance = 0.1
    if tolerance <= 0.0:
        tol_d = _EPSP25
    else:
        tol_d = max(tolerance, _EPSPT5)
    low, high = float(drange[0]), float(drange[1])
    estimate, loglik, sigma, last_var = _dopt(values, 0.0, low, high, int(m), tol_d)
    differenced = diffseries(values, estimate)
    result = Fracdiff(
        log_likelihood=loglik,
        n=n,
        msg={"fracdf": "ok", "fdcov": "ok"},
        d=estimate,
        ar=[],
        ma=[],
        sigma=math.sqrt(last_var),
        d_tol=tol_d,
        M=int(m),
        residuals=differenced,
        fitted=[original - residual for original, residual in zip(values, differenced)],
        _x=values,
        _h=h,
    )
    _attach_variance(result)
    return result


def fracdiff_var(x, fracdiff_out, h):
    """Recompute the covariance at a chosen finite-difference step."""
    if not isinstance(h, (int, float)):
        raise ValueError("h must be numeric")
    fracdiff_out._h = float(h)
    _attach_variance(fracdiff_out, force=float(h))
    return fracdiff_out


def confint_fracdiff(obj, parm=None, level=0.95):
    """Normal confidence interval for d, using the stored standard error."""
    coefs = _coef(obj)
    if not coefs or not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1) and the fit must have a coefficient")
    names = list(coefs)
    if parm is None:
        chosen = names
    elif isinstance(parm, str):
        chosen = [parm] if parm in coefs else []
    else:
        chosen = [names[index] for index in parm]
    half = (1.0 - level) / 2.0
    quantiles = (_qnorm(half), _qnorm(1.0 - half))
    rows = []
    for name in chosen:
        center = coefs[name]
        scale = obj.stderror_dpq[0]
        rows.append([center + scale * quantile for quantile in quantiles])
    return rows


def _attach_variance(result, force=None):
    step = force
    if step is None or step <= 0.0:
        step = (abs(result.log_likelihood) + 1.0) * _EPSPT5
    if step > 0.1:
        step = 0.1
    hessian = _hessian_d(result._x, result.d, result.log_likelihood, int(result.M), step)
    if hessian < 0.0:
        variance = -1.0 / hessian
        error = math.sqrt(variance)
    else:
        variance = 0.0
        error = 0.0
    result.h = step
    result.hessian_dpq = [[hessian]]
    result.covariance_dpq = [[variance]]
    result.stderror_dpq = [error]
    result.correlation_dpq = [[1.0 if error else 0.0]]


def _hessian_d(x, d, loglik, m, step):
    """Second derivative of the log likelihood, with the C's n-1 variance."""
    if d - step > 0.0:
        left = _trial_loglik(x, d - step, m)
        if d + step < 0.5:
            right = _trial_loglik(x, d + step, m)
            return (left + right - 2.0 * loglik) / (step * step)
        right = _trial_loglik(x, d - 2.0 * step, m)
        return (loglik + right - 2.0 * left) / (2.0 * step * step)
    left = _trial_loglik(x, d + step, m)
    right = _trial_loglik(x, d + 2.0 * step, m)
    return (loglik + right - 2.0 * left) / (2.0 * step * step)


def _trial_loglik(x, d, m):
    _y, slogvk, _var_n = _filter(x, d, m)
    n = len(x)
    white = sum(value * value for value in _y) / (n - 1)
    return -(n * (math.log(white) + _LIKE) + slogvk) / 2.0


def _dopt(x, dinit, low, high, m, tol_d):
    eps = math.sqrt(_EPS)
    if low + tol_d < dinit < high - tol_d:
        xx = dinit
    else:
        xx = low + _CC * (high - low)
    aa, bb = low, high
    ww = vv = xx
    dd = ee = 0.0
    fx, var_n = _pqopt(x, xx, m)
    fv = fw = fx
    tol3 = max(tol_d, 0.0) / 3.0
    nopt = 1
    last_var = var_n
    while True:
        hh = 0.5 * (aa + bb)
        tol1 = eps * (abs(xx) + 1.0) + tol3
        tol2 = 2.0 * tol1
        delta = abs(xx - hh) + 0.5 * (bb - aa)
        if delta <= tol2 or nopt >= 100:
            return xx, -fx, math.sqrt(last_var), last_var
        rr = ss = tt = 0.0
        if abs(ee) > tol1:
            rr = (xx - ww) * (fx - fv)
            ss = (xx - vv) * (fx - fw)
            tt = (xx - vv) * ss - (xx - ww) * rr
            ss = 2.0 * (ss - rr)
            if ss <= 0.0:
                ss = -ss
            else:
                tt = -tt
            rr, ee = ee, dd
        if abs(tt) >= abs(0.5 * ss * rr) or tt <= ss * (aa - xx) or tt >= ss * (bb - xx):
            ee = (aa - xx) if xx >= hh else (bb - xx)
            dd = _CC * ee
        else:
            dd = tt / ss
            uu = xx + dd
            if uu - aa < tol2 or bb - uu < tol2:
                dd = -tol1 if xx >= hh else tol1
        if abs(dd) >= tol1:
            uu = xx + dd
        else:
            uu = xx - tol1 if dd <= 0.0 else xx + tol1
        nopt += 1
        fu, last_var = _pqopt(x, uu, m)
        if fx >= fu:
            if uu >= xx:
                aa = xx
            else:
                bb = xx
            vv, fv = ww, fw
            ww, fw = xx, fx
            xx, fx = uu, fu
        else:
            if uu >= xx:
                bb = uu
            else:
                aa = uu
            if fu > fw and ww != xx:
                if fu <= fv or vv == xx or vv == ww:
                    vv, fv = uu, fu
            else:
                vv, fv = ww, fw
                ww, fw = uu, fu


def _pqopt(x, d, m):
    y, slogvk, _var_n = _filter(x, d, m)
    n = len(x)
    white = sum(value * value for value in y) / n
    objective = (n * (math.log(white) + _LIKE) + slogvk) / 2.0
    return objective, white


def _filter(x, d, m):
    """Haslett-Raftery filter. Returns the filtered series, sum of log vk, and is unused."""
    n = len(x)
    series = [0.0] + [float(value) for value in x]
    amk = [0.0] * (n + 1)
    ak = [0.0] * (n + 1)
    mcap = min(int(m), n)
    phi = [0.0] * (mcap + 1)
    vk = [0.0] * (max(mcap, 2) + 1)
    amk[1] = 0.0
    ak[1] = 1.0
    z = d / (1.0 - d)
    amk[2] = z * series[1]
    ak[2] = 1.0 - z
    phi[1] = z
    recip = 1.0 / math.gamma(1.0 - d)
    g0 = math.gamma(1.0 - 2.0 * d) * recip * recip
    vk[1] = g0
    vk[2] = g0 * (1.0 - z * z)
    for k in range(3, mcap + 1):
        km = k - 1
        t = float(km)
        u = t - d
        for j in range(1, km):
            s = t - float(j)
            phi[j] *= t * (s - d) / (u * s)
        v = d / u
        phi[km] = v
        vk[k] = vk[km] * (1.0 - v * v)
        total = 0.0
        scale = 1.0
        for j in range(1, km + 1):
            weight = phi[j]
            total += weight * series[k - j]
            scale -= weight
        amk[k] = total
        ak[k] = scale
    if mcap < n:
        pi = [0.0] * (mcap + 1)
        pi[1] = d
        running = d
        for j in range(2, mcap + 1):
            u = float(j)
            term = pi[j - 1] * ((u - 1.0 - d) / u)
            running += term
            pi[j] = term
        one_minus = 1.0 - running
        carry = 0.0
        width = float(mcap)
        edge = width * pi[mcap]
        for k in range(mcap + 1, n + 1):
            km = k - mcap
            zed = 0.0
            for j in range(1, mcap + 1):
                zed += pi[j] * series[k - j]
            if carry == 0.0:
                amk[k] = zed
                ak[k] = one_minus
            else:
                v = edge * (1.0 - (width / k) ** d) / d
                amk[k] = zed + v * carry / (float(km) - 1.0)
                ak[k] = one_minus - v
            carry += series[km]
    numerator = 0.0
    denominator = 0.0
    for k in range(1, n + 1):
        weight = ak[k]
        piece = (series[k] - amk[k]) * weight
        square = weight * weight
        if k <= mcap:
            piece /= vk[k]
            square /= vk[k]
        numerator += piece
        denominator += square
    hatmu = numerator / denominator
    slogvk = sum(math.log(vk[k]) for k in range(1, mcap + 1))
    filtered = []
    for k in range(1, n + 1):
        value = series[k] - amk[k] - hatmu * ak[k]
        if k <= mcap:
            value /= math.sqrt(vk[k])
        filtered.append(value)
    return filtered, slogvk, 0.0


def _fdsim(n, ar, ma, d, mu, y):
    """Filter white noise into an ARFIMA series. n includes the burn-in."""
    p = len(ar)
    q = len(ma)
    length = n + q
    series = [0.0] + [float(value) for value in y]
    phi = [0.0] * (length + 1)
    recip = 1.0 / math.gamma(1.0 - d)
    vk = math.gamma(1.0 - 2.0 * d) * recip * recip
    series[1] *= math.sqrt(vk)
    temp = d / (1.0 - d)
    vk *= 1.0 - temp * temp
    phi[1] = temp
    series[2] = temp * series[1] + series[2] * math.sqrt(vk)
    for k in range(3, n + q + 1):
        dk1 = float(k - 1)
        dk1d = dk1 - d
        for j in range(1, k - 1):
            dj = dk1 - float(j)
            phi[j] *= dk1 * (dj - d) / (dk1d * dj)
        temp = d / dk1d
        phi[k - 1] = temp
        vk *= 1.0 - temp * temp
        amk = sum(phi[j] * series[k - j] for j in range(1, k))
        series[k] = amk + series[k] * math.sqrt(vk)
    out = [0.0] * (n + 1)
    for k in range(1, n + 1):
        total = 0.0
        for i in range(min(p, k - 1)):
            total += ar[i] * out[k - i - 1]
        for j in range(q):
            total -= ma[j] * series[k + q - j - 1]
        out[k] = total + series[k + q]
    if mu != 0.0:
        for i in range(1, n + 1):
            out[i] += mu
    return out[1 : n + 1]


def _periodogram_d(x, bandw_exp, beta):
    values = np.asarray(_vector(x), dtype=float)
    if np.isnan(values).any():
        raise ValueError("missing values in object")
    n = len(values)
    g = math.trunc(n ** bandw_exp)
    centered = values - float(np.mean(values))
    var_x = float(np.dot(centered, centered) / n)
    cov = np.empty(n - 1)
    for k in range(1, n):
        cov[k - 1] = float(np.dot(centered[: n - k], centered[k:]) / n)
    if beta is None:
        weights = np.ones(n - 1)
        asymptotic = math.pi ** 2 / 6.0
    else:
        window = math.trunc(n ** beta)
        half = window // 2
        weights = np.zeros(n - 1)
        for k in range(1, n):
            ratio = k / window
            if k <= half:
                weights[k - 1] = 1.0 - 6.0 * ratio ** 2 * (1.0 - ratio)
            elif k <= window:
                weights[k - 1] = 2.0 * (1.0 - ratio) ** 3
        asymptotic = 0.539285 * window / n
    kk = np.arange(1, n, dtype=float)
    frequencies = 2.0 * math.pi * np.arange(1, g + 1) / n
    periodogram = np.empty(g)
    for i, frequency in enumerate(frequencies):
        periodogram[i] = var_x + 2.0 * float(np.dot(cov * weights, np.cos(frequency * kk)))
    keep = periodogram > 0.0
    y_reg = np.log(periodogram[keep] / (2.0 * math.pi))
    x_reg = 2.0 * np.log(2.0 * np.sin(frequencies[keep] / 2.0))
    design = np.column_stack((np.ones(len(x_reg)), x_reg))
    coef, _resid, _, _ = np.linalg.lstsq(design, y_reg, rcond=None)
    fitted = design @ coef
    resid = y_reg - fitted
    center = float(np.mean(x_reg))
    x_r2 = float(np.dot(x_reg - center, x_reg - center))
    var_d = asymptotic / x_r2
    var_reg = float(np.dot(resid, resid)) / ((g - 1) * x_r2)
    return {"d": float(-coef[1]), "sd_as": math.sqrt(var_d), "sd_reg": math.sqrt(var_reg)}


def _coef(obj):
    values = {"d": obj.d}
    for index, value in enumerate(obj.ar, start=1):
        values[f"ar{index}"] = value
    for index, value in enumerate(obj.ma, start=1):
        values[f"ma{index}"] = value
    return values


def _min_root(ar):
    # Smallest modulus of the roots of 1 - a1 z - ... - ap z^p.
    coeffs = [1.0] + [-float(value) for value in ar]
    roots = np.roots(coeffs[::-1])
    return float(min(abs(root) for root in roots))


def _qnorm(p):
    """Rational approximation of the standard normal quantile, enough for a 95% interval."""
    from scipy.stats import norm

    return float(norm.ppf(p))


def _vector(x):
    if isinstance(x, np.ndarray):
        if x.ndim > 1 and x.shape[1] > 2:
            raise ValueError("multivariate time series not allowed")
        return [float(value) for value in np.ravel(x, order="F")]
    return [float(value) for value in x]


def nextn(n, factors=(2, 3, 5)):
    """Smallest integer at least n whose prime factors are 2, 3, and 5."""
    n = int(n)
    if n <= 1:
        return 1
    while True:
        reduced = n
        for factor in factors:
            while reduced % factor == 0:
                reduced //= factor
        if reduced == 1:
            return n
        n += 1
