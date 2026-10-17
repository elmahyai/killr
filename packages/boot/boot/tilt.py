"""Exponential tilting, frequency smoothing, tilted bootstrap, and control variates.

The numeric steps follow exp.tilt, smooth.f, tilt.boot, and control in
R/bootfuns.q of CRAN boot 1.3-32. Strata are recoded the way tapply does
when FUN is omitted: the values become group codes 1..S in sorted order.
"""

from __future__ import annotations

import math
import warnings
from types import SimpleNamespace

import numpy as np

from boot.rng import sample_int, unif

_MISSING = object()

# Peter Acklam's normal quantile, refined against math.erf. Checked on
# the probabilities control and saddle.distn pass to qnorm.
_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_ACKLAM_LOW = 0.02425
_ACKLAM_HIGH = 1.0 - _ACKLAM_LOW
_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


class ExpTilt:
    """Tilted probabilities, the centred values, and the multipliers."""

    def __init__(self, p, theta, lambda_):
        self.p = p
        self.theta = theta
        self.lambda_ = lambda_

    def __repr__(self):
        return f"p:\n{self.p}\ntheta:\n{self.theta}\nlambda:\n{self.lambda_}"


class ControlResult:
    """Control-variate moments and quantiles from the linear approximation."""

    def __init__(self, L, tL, bias, var, k3, quantiles, distn):
        self.L = L
        self.tL = tL
        self.bias = bias
        self.var = var
        self.k3 = k3
        self.quantiles = quantiles
        self.distn = distn

    def __repr__(self):
        return (
            f"L:\n{self.L}\ntL:\n{self.tL}\nbias:\n{self.bias}\nvar:\n{self.var}\n"
            f"k3:\n{self.k3}\nquantiles:\n{self.quantiles}"
        )


def _pnorm_scalar(z):
    if math.isnan(z):
        return math.nan
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def _acklam(p):
    if p < _ACKLAM_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    if p > _ACKLAM_HIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((_ACKLAM_A[0] * r + _ACKLAM_A[1]) * r + _ACKLAM_A[2]) * r + _ACKLAM_A[3]) * r + _ACKLAM_A[4]) * r + _ACKLAM_A[5])
        * q
        / (((((_ACKLAM_B[0] * r + _ACKLAM_B[1]) * r + _ACKLAM_B[2]) * r + _ACKLAM_B[3]) * r + _ACKLAM_B[4]) * r + 1.0)
    )


def _qnorm_scalar(p):
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    z0 = _acklam(p)
    if abs(z0) > 6.0:
        return z0
    z = z0
    for _ in range(4):
        cdf = _pnorm_scalar(z)
        err = cdf - p
        if err == 0.0:
            break
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
        if pdf == 0.0 or not math.isfinite(pdf):
            break
        denom = pdf + 0.5 * z * err
        if denom == 0.0 or not math.isfinite(denom):
            break
        step = err / denom
        if not math.isfinite(step):
            break
        z = z - step
        if abs(step) <= 1e-15 * (1.0 + abs(z)):
            break
    if abs(z - z0) > 1e-7:
        return z0
    return z


def _qnorm(p):
    arr = np.asarray(p, dtype=np.float64)
    out = np.array([_qnorm_scalar(float(value)) for value in arr.reshape(-1)])
    return out.reshape(arr.shape)


def _pnorm(z):
    arr = np.asarray(z, dtype=np.float64)
    out = np.array([_pnorm_scalar(float(value)) for value in arr.reshape(-1)])
    return out.reshape(arr.shape)


def _dnorm(x):
    x = np.asarray(x, dtype=np.float64)
    return np.exp(-0.5 * x * x) * _INV_SQRT_2PI


def _attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _nrow(data):
    arr = np.asarray(data)
    if arr.ndim == 0:
        return 1
    return int(arr.shape[0])


def _as_1d(values, dtype=np.float64):
    return np.atleast_1d(np.asarray(values, dtype=dtype)).reshape(-1)


def _recode_strata(strata):
    """Group codes of as.numeric(strata), in the order tapply uses."""
    codes = _as_1d(strata, dtype=np.float64)
    levels = np.unique(codes)
    return np.searchsorted(levels, codes) + 1


def _stratum_sizes(codes):
    codes = np.asarray(codes, dtype=int)
    levels = np.unique(codes)
    sizes = {int(level): int(np.sum(codes == level)) for level in levels}
    return [int(level) for level in levels], sizes


def _counts(R):
    return _as_1d(R, dtype=np.int64)


def _r_var(x):
    x = _as_1d(x)
    n = x.size
    if n < 2:
        return math.nan
    return float(np.sum((x - np.mean(x)) ** 2) / (n - 1))


def _r_cov(x, y):
    x = _as_1d(x)
    y = _as_1d(y)
    n = x.size
    return float(np.sum((x - np.mean(x)) * (y - np.mean(y))) / (n - 1))


def _lm_slope(x, y):
    x = _as_1d(x)
    y = _as_1d(y)
    xc = x - np.mean(x)
    den = float(np.dot(xc, xc))
    if den == 0.0:
        return math.nan
    return float(np.dot(xc, y - np.mean(y)) / den)


def _const(w, eps=1e-8):
    w = _as_1d(w)
    centre = np.nanmean(w)
    return bool(np.all(np.abs(w - centre) < eps))


def _at(values, index):
    arr = _as_1d(values)
    index = int(index)
    if index < 1 or index > arr.size:
        return math.nan
    return float(arr[index - 1])


def _column(values, index):
    arr = np.asarray(values, dtype=np.float64)
    index = int(index)
    if arr.ndim == 1:
        if index != 1:
            return np.full(arr.shape, np.nan)
        return arr
    if index < 1 or index > arr.shape[1]:
        return np.full(arr.shape[0], np.nan)
    return arr[:, index - 1]


def _stat_at(value, index):
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    index = int(index)
    if index < 1 or index > arr.size:
        return math.nan
    return float(arr[index - 1])


def _first_index(index):
    arr = np.asarray(index).reshape(-1)
    return int(arr[0]), arr.size > 1


def _snapshot_rng():
    import boot.rng as rng

    return rng._mti, list(rng._mt)


def _restore_rng(state):
    import boot.rng as rng

    mti, mt = state
    rng._mti = mti
    rng._mt[:] = mt


def _load_r_seed(seed):
    """Install a saved generator state into boot.rng.

    An R `.Random.seed` vector stores the kind, then mti, then 624 state
    words as signed 32-bit integers. A state captured in-process is the
    pair `(mti, state words)`.
    """
    import boot.rng as rng

    if isinstance(seed, tuple) and len(seed) == 2 and isinstance(seed[1], (tuple, list)):
        rng._mti = int(seed[0])
        for i, word in enumerate(seed[1]):
            rng._mt[i] = int(word) & 0xFFFFFFFF
        return
    seed = _as_1d(seed, dtype=np.int64)
    rng._mti = int(seed[1])
    for i in range(624):
        rng._mt[i] = int(seed[i + 2]) & 0xFFFFFFFF


def _dump_r_seed():
    import boot.rng as rng

    if rng._mti > 624:
        unif()
    seed = [10403, int(rng._mti)]
    for word in rng._mt:
        word = int(word) & 0xFFFFFFFF
        if word >= 2**31:
            word -= 2**32
        seed.append(word)
    return seed


def _rperm(values):
    values = np.asarray(values)
    order = sample_int(values.size)
    return values[np.asarray(order, dtype=int) - 1]


def _ordinary_array(n, R, strata):
    R = int(_counts(R)[0])
    strata = np.asarray(strata, dtype=int)
    levels = np.unique(strata)
    if levels.size == 1:
        draws = sample_int(n, n * R, replace=True)
        return np.asarray(draws, dtype=np.int64).reshape((R, n), order="F")
    output = np.zeros((R, n), dtype=np.int64)
    for level in levels:
        group = np.flatnonzero(strata == level)
        k = int(group.size)
        if k == 1:
            output[:, group[0]] = group[0] + 1
        else:
            choices = sample_int(k, R * k, replace=True)
            picked = group[np.asarray(choices, dtype=int) - 1] + 1
            output[:, group] = np.asarray(picked, dtype=np.int64).reshape((R, k), order="F")
    return output


def _balanced_array(n, R, strata):
    R = int(_counts(R)[0])
    strata = np.asarray(strata, dtype=int)
    # matrix(rep(seq_len(n), R), n, R) is an n by R matrix with each column 1..n.
    output = np.tile(np.arange(1, n + 1, dtype=np.int64), (R, 1)).T.copy()
    for level in np.unique(strata):
        group = np.flatnonzero(strata == level)
        if group.size > 1:
            block = output[group, :]
            shuffled = _rperm(block.ravel(order="F"))
            output[group, :] = np.asarray(shuffled, dtype=np.int64).reshape(block.shape, order="F")
    return output.T


def _index_array(n, R, sim, strata, weights):
    if weights is None:
        if sim == "ordinary":
            return _ordinary_array(n, R, strata)
        if sim == "balanced":
            return _balanced_array(n, R, strata)
        raise ValueError("invalid value of 'sim' supplied")
    raise ValueError("weighted index arrays are rebuilt by boot.resample")


def _freq_array(i_array):
    rows, n = i_array.shape
    out = np.zeros((rows, n), dtype=np.float64)
    for r in range(rows):
        np.add.at(out[r], i_array[r] - 1, 1.0)
    return out


def _find_type(boot_out):
    boot_type = _attr(boot_out, "boot_type", None)
    if boot_type is not None:
        return boot_type
    return "boot"


def _array_weights(boot_out):
    if _find_type(boot_out) == "tilt.boot":
        return _attr(boot_out, "weights", None)
    call = _attr(boot_out, "call", None)
    if call is None:
        return None
    supplied = _attr(call, "weights", None)
    if supplied is None:
        return None
    return _attr(boot_out, "weights", None)


def _boot_array(boot_out, indices=False):
    state = _snapshot_rng()
    try:
        _load_r_seed(_attr(boot_out, "seed"))
        n = _nrow(_attr(boot_out, "data"))
        strata = _attr(boot_out, "strata", None)
        if strata is None:
            codes = np.ones(n, dtype=int)
        else:
            codes = _recode_strata(strata)
        indices_out = _index_array(
            n,
            _attr(boot_out, "R"),
            _attr(boot_out, "sim", "ordinary"),
            codes,
            _array_weights(boot_out),
        )
    finally:
        _restore_rng(state)
    if indices:
        return indices_out
    return _freq_array(indices_out)


def _normalize(wts, strata):
    wts = _as_1d(wts)
    strata = np.asarray(strata, dtype=int)
    out = wts.copy()
    for level in np.unique(strata):
        group = np.flatnonzero(strata == level)
        total = float(wts[group].sum())
        out[group] = wts[group] / total
    return out


def _imp_weights(boot_out, def_=True, q=None):
    counts = _counts(_attr(boot_out, "R"))
    if counts.size == 1:
        def_ = False
    freq = _boot_array(boot_out)
    n = freq.shape[1]
    strata = _attr(boot_out, "strata", None)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    if q is None:
        q = np.ones(n, dtype=np.float64)
    else:
        q = _as_1d(q)
    if np.any(q == 0):
        raise ValueError("0 elements not allowed in 'q'")
    p = np.asarray(_attr(boot_out, "weights"), dtype=np.float64)
    if counts.size == 1 and np.all(np.abs(p.reshape(-1) - q) / p.reshape(-1) < 1e-10):
        return np.ones(int(counts[0]), dtype=np.float64)
    q = _normalize(q, codes)
    lw_q = freq @ np.log(q)
    if p.ndim == 1:
        p = p.reshape(1, -1)
    p = np.vstack([_normalize(row, codes) for row in p])
    lw_p = np.empty((freq.shape[0], p.shape[0]), dtype=np.float64)
    for i in range(p.shape[0]):
        keep = np.flatnonzero(p[i] > 0)
        lw_p[:, i] = freq[:, keep] @ np.log(p[i, keep])
    if def_:
        ratio = np.exp(lw_p - lw_q[:, None])
        share = counts.astype(np.float64) / float(counts.sum())
        return (1.0 / (ratio @ share)).reshape(-1)
    reps = np.repeat(np.arange(counts.size), counts)
    rows = np.arange(freq.shape[0])
    return np.exp(lw_q - lw_p[rows, reps])


def _imp_moments(boot_out=None, index=1, t=_MISSING, w=None, def_=True, q=None):
    if t is _MISSING:
        if boot_out is None or _attr(boot_out, "t", None) is None:
            raise ValueError("bootstrap replicates must be supplied")
        index, several = _first_index(index)
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        t = _column(_attr(boot_out, "t"), index)
    else:
        t = np.asarray(t, dtype=np.float64)
        if t.ndim == 2:
            warnings.warn("only first column of 't' used", stacklevel=2)
            t = t[:, 0]
        else:
            t = t.reshape(-1)
    if w is None:
        if boot_out is None:
            raise ValueError("either 'boot.out' or 'w' must be specified.")
        w = _imp_weights(boot_out, def_, q)
    else:
        w = _as_1d(w)
    finite = np.isfinite(t)
    t = t[finite]
    w = w[np.flatnonzero(finite)]
    if not _const(w):
        y = t * w
        m_raw = float(np.mean(y))
        m_rat = float(np.sum(y) / np.sum(w))
        m_reg = float(np.mean(y) - _lm_slope(w, y) * (float(np.mean(w)) - 1.0))
        v_raw = float(np.mean(w * (t - m_raw) ** 2))
        v_rat = float(np.sum(w / np.sum(w) * (t - m_rat) ** 2))
        x = w * (t - m_reg) ** 2
        v_reg = float(np.mean(x) - _lm_slope(w, x) * (float(np.mean(w)) - 1.0))
    else:
        m_raw = m_rat = m_reg = float(np.mean(t))
        v_raw = v_rat = v_reg = _r_var(t)
    return SimpleNamespace(
        raw=np.array([m_raw, v_raw]),
        rat=np.array([m_rat, v_rat]),
        reg=np.array([m_reg, v_reg]),
    )


def _tilted_mean(lam, L, codes, sizes):
    tilt = np.empty(L.size, dtype=np.float64)
    for level, ns in sizes.items():
        mask = codes == level
        z = lam * L[mask] / ns
        z = z - np.max(z)
        p = np.exp(z)
        total = p.sum()
        tilt[mask] = p / total
    return tilt, float(np.dot(L, tilt))


def _solve_lambda(target, L, codes, sizes):
    """Match optim(0, tilt.dis, method = "BFGS") for this one-parameter fit.

    The objective is the squared error in the tilted mean. The step size,
    Armijo constant, and Hessian reset follow stats::optim's vmmin.
    """

    def objective(lam):
        _, mean = _tilted_mean(lam, L, codes, sizes)
        return (mean - target) ** 2

    reltol = math.sqrt(np.finfo(np.float64).eps)
    ndeps = 1e-3
    acctol = 1e-4
    stepredn = 0.2
    reltest = 10.0
    x = 0.0
    fmin = objective(x)

    def grad(point):
        return (objective(point + ndeps) - objective(point - ndeps)) / (2.0 * ndeps)

    g = grad(x)
    B = 1.0
    ilast = 0
    for _ in range(100):
        if ilast == 0:
            B = 1.0
        start = x
        gold = g
        direction = -B * g
        slope = direction * g
        if slope >= 0.0:
            ilast = 0
            B = 1.0
            direction = -g
            slope = direction * g
            if slope >= 0.0:
                break
        steplength = 1.0
        accepted = False
        trial = start
        value = fmin
        for _step in range(40):
            trial = start + steplength * direction
            if (reltest + start) == (reltest + trial):
                break
            value = objective(trial)
            if math.isfinite(value) and value <= fmin + slope * steplength * acctol:
                accepted = True
                break
            steplength *= stepredn
        if not accepted:
            break
        step = trial - start
        enough = value > -math.inf and abs(value - fmin) > reltol * (abs(fmin) + reltol)
        x = trial
        fmin = value
        if not enough:
            break
        g = grad(x)
        y = g - gold
        if step * y > 0.0:
            B = step / y
        ilast += 1
        if ilast > 2:
            ilast = 0
    return x


def _tilted_prob(lambda_, L, codes, sizes):
    lambda_ = _as_1d(lambda_)
    m = lambda_.size
    tilt = np.empty((m, L.size), dtype=np.float64)
    for i, lam in enumerate(lambda_):
        tilt[i], _ = _tilted_mean(float(lam), L, codes, sizes)
    if m == 1:
        return tilt.reshape(-1)
    return tilt


def _r_sum_times(probs, L):
    """sum(probs * L) with R's column-major recycling."""
    probs = np.asarray(probs, dtype=np.float64)
    L = _as_1d(L)
    if probs.ndim == 1:
        return float(np.sum(probs * L))
    flat = probs.ravel(order="F")
    return float(np.sum(flat * np.resize(L, flat.size)))


def exp_tilt(L, theta=None, t0=0.0, lambda_=None, strata=None):
    """Exponentially tilted multinomial weights with mean theta."""
    L = _as_1d(L)
    if strata is None:
        codes = np.ones(L.size, dtype=int)
    else:
        codes = _recode_strata(strata)
        if codes.size != L.size:
            raise ValueError("'strata' must have the same length as 'L'")
    levels, sizes = _stratum_sizes(codes)
    supplied_theta = theta is not None
    if supplied_theta:
        theta = _as_1d(theta) - float(t0)
        found = np.empty(theta.size, dtype=np.float64)
        for i, target in enumerate(theta):
            lam = _solve_lambda(float(target), L, codes, sizes)
            if lam is None:
                raise ValueError("unable to find multiplier for %f" % float(target))
            _, mean = _tilted_mean(lam, L, codes, sizes)
            msd = (mean - float(target)) ** 2
            if not math.isfinite(msd) or abs(msd) > 1e-6:
                raise ValueError("unable to find multiplier for %f" % float(target))
            found[i] = lam
        lambda_ = found
    elif lambda_ is None:
        raise ValueError("'theta' or 'lambda' required")
    probs = _tilted_prob(lambda_, L, codes, sizes)
    if not supplied_theta:
        theta_out = np.array([float(t0) + _r_sum_times(probs, L)], dtype=np.float64)
    else:
        theta_out = theta + float(t0)
    return ExpTilt(probs, theta_out, _as_1d(lambda_))


def smooth_f(theta, boot_out, index=1, t=_MISSING, width=0.5):
    """Frequency-smoothed resampling distribution centred near theta."""
    index, several = _first_index(index)
    supplied_t = t is not _MISSING
    if several and not supplied_t:
        warnings.warn("only first element of 'index' used", stacklevel=2)
        t = _column(_attr(boot_out, "t"), index)
    elif not supplied_t:
        t = _column(_attr(boot_out, "t"), index)
    else:
        t = np.asarray(t, dtype=np.float64)
    if t.ndim == 2:
        warnings.warn("only first column of 't' used", stacklevel=2)
        t = t[:, 0]
    else:
        t = np.asarray(t, dtype=np.float64).reshape(-1)
    finite = np.flatnonzero(np.isfinite(t))
    t = t[finite]
    theta = _as_1d(theta)
    m = theta.size
    variance = float(_imp_moments(boot_out, t=t).reg[1])
    eps = float(width) * math.sqrt(variance)
    if m == 1:
        weights = _dnorm((theta[0] - t) / eps) / eps
    else:
        weights = np.empty((t.size, m), dtype=np.float64)
        for i in range(m):
            weights[:, i] = _dnorm((theta[i] - t) / eps) / eps
    freq = _boot_array(boot_out)[finite, :]
    smoothed = freq.T @ np.asarray(weights, dtype=np.float64)
    if smoothed.ndim == 1:
        smoothed = smoothed.reshape(-1, 1)
    strata = _attr(boot_out, "strata", None)
    n = smoothed.shape[0]
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    out = np.empty((m, n), dtype=np.float64)
    for level in np.unique(codes):
        mask = codes == level
        block = smoothed[mask, :]
        ns = int(mask.sum())
        # matrix(..., byrow = TRUE) fills across rows from the column-major vector.
        ts = block.ravel(order="F").reshape((m, ns), order="C")
        scale = ts.sum(axis=1)
        out[:, mask] = ts / scale[:, None]
    if m == 1:
        return out.reshape(-1)
    return out


def _var_linear(L, strata=None):
    L = _as_1d(L)
    n = L.size
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    total = 0.0
    for level in np.unique(codes):
        group = np.flatnonzero(codes == level)
        total += float(np.sum(L[group] ** 2 / (group.size ** 2)))
    return total


def _k3_linear(L, strata=None):
    L = _as_1d(L)
    n = L.size
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    total = 0.0
    for level in np.unique(codes):
        group = np.flatnonzero(codes == level)
        total += float(np.sum(L[group] ** 3 / (group.size ** 3)))
    return total


def _cum3(a, b=None, c=None, unbiased=True):
    a = _as_1d(a)
    if b is None:
        b = a
    else:
        b = _as_1d(b)
    if c is None:
        c = a
    else:
        c = _as_1d(c)
    n = a.size
    mult = n / ((n - 1) * (n - 2)) if unbiased else 1.0 / n
    return float(mult * np.sum((a - np.mean(a)) * (b - np.mean(b)) * (c - np.mean(c))))


def _ols_slopes(y, X):
    y = _as_1d(y)
    design = np.column_stack([np.ones(y.size), np.asarray(X, dtype=np.float64)])
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    return coef[1:]


def _empinf_reg(boot_out, t):
    t = _as_1d(t)
    finite = np.flatnonzero(np.isfinite(t))
    t = t[finite]
    n = _nrow(_attr(boot_out, "data"))
    strata = _attr(boot_out, "strata", None)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    _, sizes = _stratum_sizes(codes)
    freq = _boot_array(boot_out)[finite, :]
    scale = np.array([sizes[int(code)] for code in codes], dtype=np.float64)
    X = freq / scale
    drop = []
    positions = np.arange(1, n + 1)
    for level in np.unique(codes):
        drop.append(int(positions[codes == level].min()))
    keep = np.ones(n, dtype=bool)
    keep[np.asarray(drop, dtype=int) - 1] = False
    beta = _ols_slopes(t, X[:, keep])
    influence = np.zeros(n, dtype=np.float64)
    influence[keep] = beta
    for level, _ns in sizes.items():
        group = np.flatnonzero(codes == level)
        influence[group] -= np.mean(influence[group])
    return influence


def _call_stat(statistic, data, second, index, kwargs):
    return _stat_at(statistic(data, second, **kwargs), index)


def _inf_jack(data, statistic, index, strata, eps, kwargs):
    n = _nrow(data)
    eps = float(eps) / n
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    _, sizes = _stratum_sizes(codes)
    w_orig = np.array([1.0 / sizes[int(code)] for code in codes], dtype=np.float64)
    observed = _call_stat(statistic, data, w_orig, index, kwargs)
    influence = np.empty(n, dtype=np.float64)
    for i in range(n):
        group = np.flatnonzero(codes == codes[i])
        w = w_orig.copy()
        w[group] = (1.0 - eps) * w[group]
        w[i] = w[i] + eps
        influence[i] = (_call_stat(statistic, data, w, index, kwargs) - observed) / eps
    return influence


def _usual_jack(data, statistic, stype, index, strata, kwargs):
    n = _nrow(data)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    _, sizes = _stratum_sizes(codes)
    influence = np.zeros(n, dtype=np.float64)
    if stype == "w":
        w0 = np.array([1.0 / sizes[int(code)] for code in codes], dtype=np.float64)
        observed = _call_stat(statistic, data, w0, index, kwargs)
        for i in range(n):
            w1 = w0.copy()
            w1[i] = 0.0
            group = codes == codes[i]
            w1[group] = w1[group] / np.sum(w1[group])
            influence[i] = (np.sum(group) - 1) * (
                observed - _call_stat(statistic, data, w1, index, kwargs)
            )
    elif stype == "f":
        f0 = np.ones(n, dtype=np.float64)
        observed = _call_stat(statistic, data, f0, index, kwargs)
        for i in range(n):
            f1 = f0.copy()
            f1[i] = 0.0
            group = codes == codes[i]
            influence[i] = (np.sum(group) - 1) * (
                observed - _call_stat(statistic, data, f1, index, kwargs)
            )
    else:
        i0 = np.arange(1, n + 1)
        observed = _call_stat(statistic, data, i0, index, kwargs)
        for i in range(n):
            i1 = np.delete(i0, i)
            group = codes == codes[i]
            influence[i] = (np.sum(group) - 1) * (
                observed - _call_stat(statistic, data, i1, index, kwargs)
            )
    return influence


def _positive_jack(data, statistic, stype, index, strata, kwargs):
    n = _nrow(data)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    _, sizes = _stratum_sizes(codes)
    influence = np.zeros(n, dtype=np.float64)
    if stype == "w":
        w0 = np.array([1.0 / sizes[int(code)] for code in codes], dtype=np.float64)
        observed = _call_stat(statistic, data, w0, index, kwargs)
        for i in range(n):
            extended = np.concatenate([codes, [codes[i]]])
            _, extended_sizes = _stratum_sizes(extended)
            w1 = np.array([1.0 / extended_sizes[int(code)] for code in codes], dtype=np.float64)
            w1[i] = 2.0 * w1[i]
            group = codes == codes[i]
            w1[group] = w1[group] / np.sum(w1[group])
            influence[i] = (np.sum(group) + 1) * (
                _call_stat(statistic, data, w1, index, kwargs) - observed
            )
    elif stype == "f":
        f0 = np.ones(n, dtype=np.float64)
        observed = _call_stat(statistic, data, f0, index, kwargs)
        for i in range(n):
            f1 = f0.copy()
            f1[i] = 2.0
            group = codes == codes[i]
            influence[i] = (np.sum(group) + 1) * (
                _call_stat(statistic, data, f1, index, kwargs) - observed
            )
    else:
        i0 = np.arange(1, n + 1)
        observed = _call_stat(statistic, data, i0, index, kwargs)
        for i in range(n):
            i1 = np.concatenate([i0, [i + 1]])
            group = codes == codes[i]
            influence[i] = (np.sum(group) + 1) * (
                _call_stat(statistic, data, i1, index, kwargs) - observed
            )
    return influence


def _empinf(boot_out=None, data=None, statistic=None, type=None, stype=None, index=1, t=None, strata=None, eps=0.001, **kwargs):
    if boot_out is not None:
        if _attr(boot_out, "sim", None) == "parametric":
            raise ValueError("influence values cannot be found from a parametric bootstrap")
        data = _attr(boot_out, "data")
        if statistic is None:
            statistic = _attr(boot_out, "statistic")
        if stype is None:
            stype = _attr(boot_out, "stype")
        if _attr(boot_out, "strata", None) is not None:
            strata = _attr(boot_out, "strata")
    else:
        if data is None:
            raise ValueError("neither 'data' nor bootstrap object specified")
        if statistic is None:
            raise ValueError("neither 'statistic' nor bootstrap object specified")
        if stype is None:
            stype = "w"
    n = _nrow(data)
    if strata is None:
        strata = np.ones(n, dtype=int)
    index, several = _first_index(index)
    if type is None:
        if t is not None:
            type = "reg"
        elif stype == "w":
            type = "inf"
        elif boot_out is not None and _attr(boot_out, "sim") not in ("parametric", "permutation"):
            replicates = int(np.sum(_counts(_attr(boot_out, "R"))))
            type = "jack" if replicates < n else "reg"
        else:
            type = "jack"
    if type == "inf":
        if stype != "w":
            raise ValueError("'stype' must be \"w\" for type=\"inf\"")
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        if t is not None:
            warnings.warn("input 't' ignored; type=\"inf\"", stacklevel=2)
        return _inf_jack(data, statistic, index, strata, eps, kwargs)
    if type == "reg":
        if boot_out is None:
            raise ValueError("bootstrap object needed for type=\"reg\"")
        if t is None:
            if several:
                warnings.warn("only first element of 'index' used", stacklevel=2)
            t = _column(_attr(boot_out, "t"), index)
        return _empinf_reg(boot_out, t)
    if type == "jack":
        if t is not None:
            warnings.warn("input 't' ignored; type=\"jack\"", stacklevel=2)
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        return _usual_jack(data, statistic, stype, index, strata, kwargs)
    if type == "pos":
        if t is not None:
            warnings.warn("input 't' ignored; type=\"pos\"", stacklevel=2)
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        return _positive_jack(data, statistic, stype, index, strata, kwargs)
    raise ValueError("unknown influence type")


def _linear_approx(boot_out, L=None, index=1, type=None, t0=None, t=None, **kwargs):
    freq = _boot_array(boot_out)
    n = freq.shape[1]
    index, several = _first_index(index)
    if several and (t0 is None or t is None):
        warnings.warn("only first element of 'index' used", stacklevel=2)
    if t0 is None:
        t0 = _at(_attr(boot_out, "t0"), index)
        if L is None:
            L = _empinf(boot_out, index=index, type=type, **kwargs)
    elif t is None and L is None:
        warnings.warn("input 't0' ignored: neither 't' nor 'L' supplied", stacklevel=2)
        t0 = _at(t0, index)
        L = _empinf(boot_out, index=index, type=type, **kwargs)
    elif L is None:
        L = _empinf(boot_out, type=type, t=t, **kwargs)
    L = _as_1d(L)
    replicates = int(freq.shape[0])
    tL = np.full(replicates, float(t0), dtype=np.float64)
    strata = _attr(boot_out, "strata", None)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = _recode_strata(strata)
    for level in np.unique(codes):
        group = np.flatnonzero(codes == level)
        tL = tL + freq[:, group] @ L[group] / group.size
    return np.asarray(tL, dtype=np.float64).reshape(-1)


def _sgn(x, eps=1e-10):
    if abs(x) < eps:
        return 0.0
    return 1.0 if x > 0.0 else -1.0


def _saddle_simple(A, u, strata=None, init=0.1, mu=None):
    A = np.asarray(A, dtype=np.float64)
    if A.ndim == 1:
        A = A.reshape(-1, 1)
    n, d = A.shape
    u = _as_1d(u)
    if u.size != d:
        raise ValueError(
            "number of columns of 'A' (%d) not equal to length of 'u' (%d)" % (d, u.size)
        )
    if mu is None:
        mu = np.full(n, 0.5, dtype=np.float64)
    else:
        mu = _as_1d(mu)
    if strata is None:
        codes = np.ones(n, dtype=int)
    else:
        codes = np.asarray(strata, dtype=int)
        if codes.min() < 1 or np.unique(codes).size != codes.max():
            codes = _recode_strata(codes)
    levels, sizes = _stratum_sizes(codes)
    sm = np.array([float(mu[codes == level].sum()) for level in codes], dtype=np.float64)
    p = mu / sm

    def weights(al):
        al = _as_1d(al)
        log_w = np.log(np.maximum(p, 1e-300)) + A @ al
        w = np.empty(n, dtype=np.float64)
        for level in sizes:
            group = np.flatnonzero(codes == level)
            w[group] = np.exp(log_w[group] - np.max(log_w[group]))
        return w

    def deriv(al):
        w = weights(al)
        total = np.zeros(d, dtype=np.float64)
        for level, ns in sizes.items():
            group = np.flatnonzero(codes == level)
            sw = float(w[group].sum())
            if sw <= 0.0 or not math.isfinite(sw):
                return np.full(d, np.nan)
            total += ns * (w[group] @ A[group, :]) / sw
        return total - u

    al = np.full(d, float(np.asarray(init, dtype=np.float64).reshape(-1)[0]))
    converged = False
    for _ in range(60):
        grad = deriv(al)
        if not np.all(np.isfinite(grad)):
            break
        if float(np.max(np.abs(grad))) < 1e-12:
            converged = True
            break
        if d == 1:
            w = weights(al)
            slope = 0.0
            finite_slope = True
            for level, ns in sizes.items():
                group = np.flatnonzero(codes == level)
                sw = float(w[group].sum())
                if sw <= 0.0 or not math.isfinite(sw):
                    finite_slope = False
                    break
                mean = float(np.dot(w[group], A[group, 0]) / sw)
                second = float(np.dot(w[group], A[group, 0] ** 2) / sw)
                slope += ns * (second - mean ** 2)
            if not finite_slope or slope == 0.0 or not math.isfinite(slope):
                break
            step = float(grad[0] / slope)
            if not math.isfinite(step):
                break
            al = al - step
            if abs(step) < 1e-14 * (1.0 + abs(float(al[0]))):
                converged = True
                break
        else:
            break
    else:
        grad = deriv(al)
        converged = bool(np.all(np.isfinite(grad)) and float(np.max(np.abs(grad))) < 1e-8)
    ahat = al
    log_w = np.log(p) + A @ ahat
    if not np.all(np.isfinite(log_w)):
        return SimpleNamespace(spa=np.array([math.nan, math.nan]), zeta_hat=np.full(d, math.nan))
    # Shift each stratum so the weights stay finite. The shift cancels in the ratios.
    w = np.empty(n, dtype=np.float64)
    for level in sizes:
        group = np.flatnonzero(codes == level)
        shifted = log_w[group] - np.max(log_w[group])
        w[group] = np.exp(shifted)
    if strata is None or np.unique(codes).size == 1:
        ns = float(n)
        sw = float(w.sum())
        if sw <= 0.0 or not math.isfinite(sw):
            return SimpleNamespace(spa=np.array([math.nan, math.nan]), zeta_hat=np.full(d, math.nan))
        # max(log_w) was removed, so put it back into the cumulant.
        Khat = ns * (math.log(sw) + float(np.max(log_w))) - float(np.dot(ahat, u))
        if d == 1:
            K2hat = ns * (float(np.sum(w * A[:, 0] ** 2) / sw) - (float(np.sum(w * A[:, 0]) / sw) ** 2))
        else:
            K2hat = math.nan
    else:
        Khat = 0.0
        for level, ns in sizes.items():
            group = np.flatnonzero(codes == level)
            sw = float(w[group].sum())
            if sw <= 0.0:
                return SimpleNamespace(spa=np.array([math.nan, math.nan]), zeta_hat=np.full(d, math.nan))
            Khat += ns * (math.log(sw) + float(np.max(log_w[group])))
        Khat -= float(np.dot(ahat, u))
        temp = np.zeros((d, d), dtype=np.float64)
        for level, ns in sizes.items():
            group = np.flatnonzero(codes == level)
            sw = float(w[group].sum())
            saw = w[group] @ A[group, :]
            sa2w = (A[group, :] * w[group, None]).T @ A[group, :]
            temp += ns / sw * (sa2w - np.outer(saw, saw) / sw)
        K2hat = abs(float(np.linalg.det(temp))) if d > 1 else abs(float(temp[0, 0]))
    if not converged or not math.isfinite(Khat) or not math.isfinite(K2hat) or K2hat <= 0.0:
        return SimpleNamespace(spa=np.array([math.nan, math.nan]), zeta_hat=np.full(d, math.nan))
    gs = math.exp(Khat) / (math.sqrt(2.0 * math.pi * K2hat) ** d)
    if d == 1:
        root = _sgn(float(ahat[0])) * math.sqrt(-2.0 * Khat)
        v = float(ahat[0]) * math.sqrt(K2hat)
        if root == 0.0 or not math.isfinite(root) or v == 0.0:
            Gs = math.nan
        else:
            Gs = _pnorm_scalar(root + math.log(v / root) / root)
    else:
        Gs = math.nan
    return SimpleNamespace(spa=np.array([gs, Gs], dtype=np.float64), zeta_hat=ahat.copy())


def _linspace_drop_ends(start, stop, length):
    """seq.int(start, stop, length.out) with the first element removed, then the last."""
    length = int(length)
    if length < 3:
        return np.array([], dtype=np.float64)
    grid = np.linspace(start, stop, length)
    return grid[1:-1]


def _natural_cubic_predict(x, y, xnew):
    x = _as_1d(x)
    y = _as_1d(y)
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    y = y[order]
    # Aggregate duplicate abscissae the way smooth.spline does before fitting.
    unique_x = [x[0]]
    unique_y = [y[0]]
    count = [1]
    for i in range(1, x.size):
        if x[i] == unique_x[-1]:
            unique_y[-1] += y[i]
            count[-1] += 1
        else:
            unique_x.append(x[i])
            unique_y.append(y[i])
            count.append(1)
    x = np.asarray(unique_x, dtype=np.float64)
    y = np.asarray(unique_y, dtype=np.float64) / np.asarray(count, dtype=np.float64)
    n = x.size
    if n < 4:
        raise ValueError("need at least four unique 'x' values")
    h = np.diff(x)
    system = np.zeros((n, n), dtype=np.float64)
    rhs = np.zeros(n, dtype=np.float64)
    system[0, 0] = 1.0
    system[-1, -1] = 1.0
    for i in range(1, n - 1):
        system[i, i - 1] = h[i - 1]
        system[i, i] = 2.0 * (h[i - 1] + h[i])
        system[i, i + 1] = h[i]
        rhs[i] = 6.0 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    second = np.linalg.solve(system, rhs)
    slope_left = (y[1] - y[0]) / h[0] - h[0] * (2.0 * second[0] + second[1]) / 6.0
    slope_right = (y[-1] - y[-2]) / h[-1] + h[-1] * (second[-2] + 2.0 * second[-1]) / 6.0
    query = np.asarray(xnew, dtype=np.float64).reshape(-1)
    out = np.empty(query.size, dtype=np.float64)
    for i, xv in enumerate(query):
        if xv <= x[0]:
            out[i] = y[0] + slope_left * (xv - x[0])
            continue
        if xv >= x[-1]:
            out[i] = y[-1] + slope_right * (xv - x[-1])
            continue
        j = int(np.searchsorted(x, xv) - 1)
        dx = h[j]
        A = (x[j + 1] - xv) / dx
        B = (xv - x[j]) / dx
        out[i] = (
            A * y[j]
            + B * y[j + 1]
            + ((A**3 - A) * second[j] + (B**3 - B) * second[j + 1]) * (dx**2) / 6.0
        )
    return out


class _SplineDistn:
    def __init__(self, x, y):
        self.x = _as_1d(x)
        self.y = _as_1d(y)

    def predict(self, x):
        return _natural_cubic_predict(self.x, self.y, x)


def _saddle_distn(A, alpha, t0, strata=None):
    """Saddlepoint quantiles for the one-column multinomial case control uses."""
    A = np.asarray(A, dtype=np.float64).reshape(-1, 1)
    n = A.shape[0]
    alpha = _as_1d(alpha)
    t0 = _as_1d(t0)
    npts = 20
    ep1 = min(float(np.min(alpha)), 0.01) / 10.0
    ep2 = (1.0 - max(float(np.max(alpha)), 0.99)) / 10.0
    zeta = np.full(npts, np.nan)
    spa = np.full((npts, 2), np.nan)
    pts = []
    # i and i1 follow R's 1-based counts of stored saddlepoint rows.
    i = 0
    centre = float(t0[0])
    scale = float(t0[1])
    mu = np.full(n, 0.5)

    def one(point):
        return _saddle_simple(A, np.array([point]), strata=strata, init=0.1, mu=mu)

    def store(row, sad, point):
        zeta[row - 1] = sad.zeta_hat[0]
        spa[row - 1] = sad.spa
        pts.append(point)

    t1 = centre - 2.0 * scale
    sad = one(t1)
    bdu = None
    bdl = None
    while math.isnan(sad.spa[1]) or sad.spa[1] > ep1 or sad.spa[1] < ep1 / 100.0:
        if not math.isnan(sad.spa[1]) and sad.spa[1] > ep1:
            i += 1
            store(i, sad, t1)
            bdu = t1
        else:
            bdl = t1
        if i == npts // 2:
            raise ValueError("unable to find range")
        if bdl is None:
            t1 = 2.0 * t1 - centre
        elif bdu is None:
            t1 = (centre + bdl) / 2.0
        else:
            t1 = (bdu + bdl) / 2.0
        sad = one(t1)
    i += 1
    i1 = i
    store(i, sad, t1)

    t2 = centre + 2.0 * scale
    sad = one(t2)
    bdu = None
    bdl = None
    while math.isnan(sad.spa[1]) or (1.0 - sad.spa[1]) > ep2 or (1.0 - sad.spa[1]) < ep2 / 100.0:
        if not math.isnan(sad.spa[1]) and (1.0 - sad.spa[1]) > ep2:
            i += 1
            store(i, sad, t2)
            bdl = t2
        else:
            bdu = t2
        if (i - i1) == npts // 2:
            raise ValueError("unable to find range")
        if bdu is None:
            t2 = 2.0 * t2 - centre
        elif bdl is None:
            t2 = (centre + bdu) / 2.0
        else:
            t2 = (bdu + bdl) / 2.0
        sad = one(t2)
    i += 1
    store(i, sad, t2)

    if npts % 2 == 0:
        tt1 = _linspace_drop_ends(t1, centre, npts // 2 - i1 + 2)
        tt2 = _linspace_drop_ends(centre, t2, npts // 2 + i1 - i + 2)
    else:
        ex = 1 if (t1 + t2) > 2.0 * centre else 0
        ll = npts // 2 + 2
        tt1 = _linspace_drop_ends(t1, centre, ll - i1 + 1 - ex)
        tt2 = _linspace_drop_ends(centre, t2, ll + i1 - i + ex)
    interior = np.concatenate([tt1, tt2]) if tt1.size or tt2.size else np.array([], dtype=np.float64)
    if interior.size != npts - i:
        raise ValueError("unable to find range")
    for j, point in enumerate(interior):
        sad = one(float(point))
        zeta[i + j] = sad.zeta_hat[0]
        spa[i + j] = sad.spa
    all_pts = np.concatenate([np.asarray(pts, dtype=np.float64), interior])
    keep = (np.abs(zeta[: all_pts.size]) > 1e-6) & (np.abs(spa[: all_pts.size, 1] - 0.5) < 0.5 - 1e-10)
    kept_pts = all_pts[keep]
    kept_cdf = spa[: all_pts.size, 1][keep]
    distn = _SplineDistn(_qnorm(kept_cdf), kept_pts)
    quantiles = distn.predict(_qnorm(alpha))
    return quantiles, distn


def _subscript(values, index):
    """R's x[index] for positive indexes, dropping exact zeros after truncation."""
    values = _as_1d(values)
    index = np.trunc(_as_1d(index)).astype(int)
    picked = [values[i - 1] for i in index if i != 0]
    return np.asarray(picked, dtype=np.float64)


def _recycle_columns(left, right):
    left = _as_1d(left)
    right = _as_1d(right)
    n = max(left.size, right.size)
    if left.size != n:
        left = np.resize(left, n)
    if right.size != n:
        right = np.resize(right, n)
    return np.column_stack([left, right])


def _has_weights(boot_out):
    call = _attr(boot_out, "call", None)
    if call is None:
        return False
    return _attr(call, "weights", None) is not None


def control(boot_out, L=None, distn=None, index=1, t0=None, t=None, bias_adj=False, alpha=None, **kwargs):
    """Control-variate bias, or moments and quantiles from the linear approximation."""
    if _has_weights(boot_out):
        raise ValueError("control methods undefined when 'boot.out' has weights")
    if alpha is None:
        alpha = np.array([1, 2.5, 5, 10, 20, 50, 80, 90, 95, 97.5, 99], dtype=np.float64) / 100.0
    else:
        alpha = _as_1d(alpha)
    statistic = _attr(boot_out, "statistic")
    data = _attr(boot_out, "data")
    replicates = _attr(boot_out, "R")
    if bias_adj:
        index, several = _first_index(index)
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        freq = _boot_array(boot_out)
        f_big = freq.sum(axis=0)
        stype = _attr(boot_out, "stype")
        if stype == "i":
            n = freq.shape[1]
            i_big = np.repeat(np.arange(1, n + 1), f_big.astype(np.int64))
            t_big = _call_stat(statistic, data, i_big, index, kwargs)
        elif stype == "f":
            t_big = _call_stat(statistic, data, f_big, index, kwargs)
        elif stype == "w":
            scale = float(np.sum(_counts(replicates)))
            t_big = _call_stat(statistic, data, f_big / scale, index, kwargs)
        else:
            raise ValueError("unknown 'stype'")
        return float(np.mean(_column(_attr(boot_out, "t"), index)) - t_big)

    supplied = t is not None and t0 is not None
    if not supplied:
        index, several = _first_index(index)
        if several:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        if L is None:
            L = _empinf(boot_out, index=index, **kwargs)
        tL = _linear_approx(boot_out, L, index, **kwargs)
        t = _column(_attr(boot_out, "t"), index)
        t0 = _at(_attr(boot_out, "t0"), index)
    else:
        if L is None:
            L = _empinf(boot_out, t=t, **kwargs)
        tL = _linear_approx(boot_out, L, t0=t0, **kwargs)
        t = np.asarray(t, dtype=np.float64).reshape(-1)
        t0 = float(np.asarray(t0, dtype=np.float64).reshape(-1)[0])
    L = _as_1d(L)
    finite = np.flatnonzero(np.isfinite(t))
    t = t[finite]
    tL = _as_1d(tL)[finite]
    R = t.size
    dL = t - tL
    bias_L = float(np.mean(dL))
    strata = _attr(boot_out, "strata", None)
    if strata is None:
        codes = np.ones(L.size, dtype=int)
    else:
        codes = _recode_strata(strata)
    var_L = _var_linear(L, codes) + 2.0 * _r_cov(tL, dL) + _r_var(dL)
    k3_L = (
        _k3_linear(L, codes)
        + 3.0 * _cum3(tL, dL)
        + 3.0 * _cum3(dL, tL)
        + _cum3(dL)
    )
    if distn is None:
        dist_q, distn = _saddle_distn((t0 + L) / L.size, (np.arange(1, R + 1)) / (R + 1), np.array([t0, math.sqrt(var_L)]), codes)
    else:
        predicted = distn.predict(_qnorm((np.arange(1, R + 1)) / (R + 1)))
        dist_q = np.asarray(predicted, dtype=np.float64).reshape(-1)
    order = np.argsort(tL, kind="mergesort")
    distn_L = np.sort(dL[order] + dist_q)
    q_out = _subscript(distn_L, (R + 1) * alpha)
    quantiles = _recycle_columns(alpha, q_out)
    return ControlResult(L, tL, bias_L, float(var_L), float(k3_L), quantiles, distn)


def _quantile_type7(x, probs):
    x = np.sort(_as_1d(x))
    n = x.size
    probs = _as_1d(probs)
    out = np.empty(probs.size, dtype=np.float64)
    for i, p in enumerate(probs):
        h = 1.0 + (n - 1) * float(p)
        j = int(math.floor(h))
        g = h - j
        if j < 1:
            out[i] = x[0]
        elif j >= n:
            out[i] = x[-1]
        elif g == 0.0:
            out[i] = x[j - 1]
        else:
            out[i] = (1.0 - g) * x[j - 1] + g * x[j]
    return out


def _rbind(top, bottom):
    if top is None:
        return None if bottom is None else np.asarray(bottom, dtype=np.float64)
    if bottom is None:
        return np.asarray(top, dtype=np.float64)
    return np.vstack([np.atleast_2d(np.asarray(top, dtype=np.float64)), np.atleast_2d(np.asarray(bottom, dtype=np.float64))])


def tilt_boot(data, statistic, R, sim="ordinary", stype="i", strata=None, L=None, theta=None, alpha=None, tilt=True, width=0.5, index=1, **kwargs):
    """Uniform bootstrap followed by exponentially tilted or smoothed resamples."""
    if sim not in ("ordinary", "balanced"):
        raise ValueError("invalid value of 'sim' supplied")
    counts = _counts(R)
    supplied_alpha = alpha is not None
    if alpha is None:
        alpha = np.array([0.025, 0.975], dtype=np.float64)
    else:
        alpha = _as_1d(alpha)
    if theta is not None and counts.size != _as_1d(theta).size + 1:
        raise ValueError("'R' and 'theta' have incompatible lengths")
    if not tilt and int(counts[0]) == 0:
        raise ValueError("R[1L] must be positive for frequency smoothing")
    n = _nrow(data)
    if strata is None:
        strata = np.ones(n, dtype=int)
    else:
        strata = _as_1d(strata, dtype=np.float64)
    index, _several = _first_index(index)
    try:
        from boot.resample import boot as resample_boot
    except ImportError as exc:
        raise ImportError("tilt_boot needs boot.resample.boot") from exc
    if int(counts[0]) > 0:
        if theta is None and counts.size != alpha.size + 1:
            raise ValueError("'R' and 'alpha' have incompatible lengths")
        boot0 = resample_boot(
            data,
            statistic,
            R=int(counts[0]),
            sim=sim,
            stype=stype,
            strata=strata,
            **kwargs,
        )
        if theta is None:
            if np.any(np.concatenate([alpha, 1.0 - alpha]) * (int(counts[0]) + 1) <= 5):
                warnings.warn("extreme values used for quantiles", stacklevel=2)
            theta = _quantile_type7(_column(_attr(boot0, "t"), index), alpha)
        else:
            theta = _as_1d(theta)
    else:
        tilt = True
        if theta is None:
            raise ValueError("'theta' must be supplied if R[1L] = 0")
        if supplied_alpha:
            warnings.warn("'alpha' ignored; R[1L] = 0", stacklevel=2)
        theta = _as_1d(theta)
        if stype == "i":
            original = np.arange(1, n + 1)
        elif stype == "f":
            original = np.ones(n, dtype=np.float64)
        else:
            original = np.ones(n, dtype=np.float64) / n
        observed = np.asarray(statistic(data, original, **kwargs), dtype=np.float64).reshape(-1)
        boot0 = SimpleNamespace(
            t0=observed,
            t=None,
            R=np.array([0], dtype=int),
            data=data,
            statistic=statistic,
            sim=sim,
            stype=stype,
            strata=strata,
            weights=None,
            call=None,
            seed=_dump_r_seed(),
            boot_type="boot",
        )
    if L is None and tilt:
        if int(counts[0]) > 0:
            L = _empinf(boot0, index=index, **kwargs)
        else:
            L = _empinf(
                data=data,
                statistic=statistic,
                stype=stype,
                index=index,
                strata=strata,
                **kwargs,
            )
    if tilt:
        probs = exp_tilt(L, theta=theta, strata=strata, t0=_at(_attr(boot0, "t0"), index)).p
    else:
        probs = smooth_f(theta, boot0, index=index, width=width)
    boot1 = resample_boot(
        data,
        statistic,
        R=counts[1:],
        sim=sim,
        stype=stype,
        strata=strata,
        weights=probs,
        **kwargs,
    )
    boot0.t = _rbind(_attr(boot0, "t", None), _attr(boot1, "t"))
    boot0.weights = _rbind(_attr(boot0, "weights", None), _attr(boot1, "weights"))
    boot0.R = np.concatenate([_counts(_attr(boot0, "R")), _counts(_attr(boot1, "R"))])
    boot0.call = SimpleNamespace(weights=probs)
    boot0.theta = theta
    boot0.boot_type = "tilt.boot"
    return boot0
