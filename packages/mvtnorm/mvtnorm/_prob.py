"""Multivariate normal and t probabilities, quantiles, and the three algorithms."""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.stats import cauchy, nct

from boot import rng as _rng
from extradistr._special import pnorm, pt, qt

from mvtnorm._dens import _as_1d, match_arg
from mvtnorm._lib import bvtl, miwa, mvtdst_df, pack_corr, tvtl

_EPS = float(np.finfo(float).eps)
_SQRT_EPS = math.sqrt(_EPS)


class Prob(float):
    """A probability with the error, message, and algorithm R attaches."""

    def __new__(cls, value, error=0.0, msg="", algorithm=None):
        obj = float.__new__(cls, value)
        obj.error = error
        obj.msg = msg
        obj.algorithm = algorithm
        return obj


class GenzBretz:
    def __init__(self, maxpts=25000, abseps=0.001, releps=0):
        self.maxpts = maxpts
        self.abseps = abseps
        self.releps = releps

    def __repr__(self):
        return f"GenzBretz(maxpts={self.maxpts}, abseps={self.abseps}, releps={self.releps})"


class Miwa:
    def __init__(self, steps=128, checkCorr=True, maxval=1e3):
        if steps > 4097:
            raise ValueError("maximum number of steps is 4097")
        self.steps = steps
        self.checkCorr = checkCorr
        self.maxval = maxval


class TVPACK:
    def __init__(self, abseps=1e-6):
        self.eps = abseps


def _quote(name):
    return f"'{name}'"


def _recycle(lower, upper, mean):
    parts = [_as_1d(lower), _as_1d(upper), _as_1d(mean)]
    n = max(len(p) for p in parts)
    out = []
    for p in parts:
        if len(p) == 0 or n % len(p) != 0:
            warnings.warn("longer object length is not a multiple of shorter object length")
        reps = int(math.ceil(n / max(len(p), 1)))
        out.append(np.resize(p, n))
    return out


def _is_corr(corr):
    corr = np.asarray(corr, dtype=float)
    if corr.ndim != 2 or corr.shape[0] != corr.shape[1]:
        return False
    one = 1 + _SQRT_EPS
    diag = np.diag(corr)
    return np.min(corr) >= -one and np.max(corr) <= one and np.allclose(diag, 1.0, atol=1e-8, rtol=1e-8)


def checkmvArgs(lower, upper, mean, corr, sigma):
    lower = _as_1d(lower)
    upper = _as_1d(upper)
    mean = _as_1d(mean)
    if lower.size == 0 or np.any(np.isnan(lower)):
        raise ValueError(f"{_quote('lower')} not specified or contains NA")
    if upper.size == 0 or np.any(np.isnan(upper)):
        raise ValueError(f"{_quote('upper')} not specified or contains NA")
    lower, upper, mean = _recycle(lower, upper, mean)
    if np.any(lower > upper):
        raise ValueError(f"at least one element of {_quote('lower')} is larger than {_quote('upper')}")
    if np.any(np.isnan(mean)):
        raise ValueError("mean contains NA")
    if corr is None and sigma is None:
        corr = np.eye(len(lower))
    elif corr is not None and sigma is not None:
        warnings.warn(f"both {_quote('corr')} and {_quote('sigma')} specified: ignoring {_quote('sigma')}")
        sigma = None
    uni = False
    if corr is not None:
        corr = np.asarray(corr, dtype=float)
        if corr.ndim != 2:
            if corr.size == 1:
                uni = True
            if corr.size != len(lower):
                raise ValueError(f"{_quote('diag(corr)')} and {_quote('lower')} are of different length")
        elif corr.size == 1:
            uni = True
            corr = float(corr.ravel()[0])
            if len(lower) != 1:
                raise ValueError(f"{_quote('corr')} and {_quote('lower')} are of different length")
        else:
            if np.diag(corr).size != len(lower):
                raise ValueError(f"{_quote('diag(corr)')} and {_quote('lower')} are of different length")
            if not _is_corr(corr):
                raise ValueError(f"{_quote('corr')} is not a correlation matrix")
    if sigma is not None:
        sigma = np.asarray(sigma, dtype=float)
        if sigma.ndim != 2:
            if sigma.size == 1:
                uni = True
            if sigma.size != len(lower):
                raise ValueError(f"{_quote('diag(sigma)')} and {_quote('lower')} are of different length")
        elif sigma.size == 1:
            uni = True
            sigma = float(sigma.ravel()[0])
            if len(lower) != 1:
                raise ValueError(f"{_quote('sigma')} and {_quote('lower')} are of different length")
        else:
            if np.diag(sigma).size != len(lower):
                raise ValueError(f"{_quote('diag(sigma)')} and {_quote('lower')} are of different length")
            if not np.allclose(sigma, sigma.T, atol=1e-8, rtol=1e-8) or np.any(np.diag(sigma) < 0):
                raise ValueError(f"{_quote('sigma')} is not a covariance matrix")
    return {"lower": lower, "upper": upper, "mean": mean, "corr": corr, "sigma": sigma, "uni": uni}


def _cov2cor(sigma):
    d = np.sqrt(np.diag(sigma))
    return sigma / np.outer(d, d)


def _rng_state():
    return (list(_rng._mt), _rng._mti)


def _restore(state):
    _rng._mt[:] = state[0]
    _rng._mti = state[1]


def _with_seed(seed):
    """Return the state to restore, after applying seed the way R's set.seed does."""
    state = _rng_state()
    if seed is not None:
        _rng.set_seed(int(seed))
    return state


def _infin(lower, upper):
    infin = np.full(len(lower), 2, dtype=int)
    infin[np.isinf(upper) & (upper > 0)] = 1
    infin[np.isinf(lower) & (lower < 0)] = 0
    infin[(np.isinf(lower) & (lower < 0)) & (np.isinf(upper) & (upper > 0))] = -1
    return infin


def _messages(inform):
    if inform == 0:
        return "Normal Completion"
    if inform == 1:
        return "Completion with error > abseps"
    if inform == 2:
        return "Dimension greater 1000 or dimension < 1"
    if inform == 3:
        return "Covariance matrix not positive semidefinite"
    return inform


def probval_genzbretz(algo, n, df, lower, upper, infin, corr, delta):
    if np.isinf(df):
        df = 0
    lower = np.array(lower, dtype=float)
    upper = np.array(upper, dtype=float)
    lower[np.isinf(lower) & (lower < 0)] = 0.0
    upper[np.isinf(upper) & (upper > 0)] = 0.0
    value, error, inform = mvtdst_df(
        n, int(df), lower, upper, infin, corr, delta, algo.maxpts, algo.abseps, algo.releps
    )
    return value, error, inform


def probval_miwa(algo, n, df, lower, upper, infin, corr, delta):
    if not (df == 0 or np.isinf(df)):
        raise ValueError("Miwa algorithm cannot compute t-probabilities")
    if n > 20:
        raise ValueError("Miwa algorithm cannot compute probabilities for dimension n > 20")
    upper = np.array(upper, dtype=float)
    lower = np.array(lower, dtype=float)
    if np.any(np.asarray(delta) != 0):
        upper = upper - delta
        lower = lower - delta
    if algo.checkCorr:
        try:
            np.linalg.solve(corr, np.eye(n))
        except np.linalg.LinAlgError as exc:
            raise ValueError("Miwa algorithm cannot compute probabilities for singular problems") from exc
    if len(set(infin.tolist())) != 1:
        warnings.warn(f"Approximating +/-Inf by +/-{algo.maxval}")
        lower = lower.copy()
        upper = upper.copy()
        lower[infin <= 0] = -algo.maxval
        upper[np.abs(infin) == 1] = algo.maxval
    value = miwa(algo.steps, corr, upper, lower, infin)
    return value, math.nan, 0


def probval_tvpack(algo, n, df, lower, upper, infin, corr, delta):
    if df > 0 and np.any(np.asarray(delta) != 0):
        raise ValueError("TVPACK only possible for the central t-distribution.")
    if abs(df - int(df)) > 1e-7:
        raise ValueError("'df' must be integer (valued)")
    nu = int(df)
    upp = np.asarray(upper, dtype=float) - np.asarray(delta, dtype=float)
    low = np.asarray(lower, dtype=float) - np.asarray(delta, dtype=float)
    if np.any(infin < 0) or np.any(infin > 1) or len(set(infin.tolist())) > 1:
        raise ValueError("TVPACK either needs all(lower == -Inf) or all(upper == Inf).")
    if np.all(infin == 1):
        upp = -low
    if n == 1:
        if nu == 0:
            val = pnorm(float(upp[0])) - pnorm(float(low[0]))
        else:
            val = pt(float(upp[0]), nu) - pt(float(low[0]), nu)
        err = 0.0
    elif n == 2:
        val = bvtl(nu, upp[0], upp[1], corr[1, 0])
        err = math.nan
    elif n == 3:
        cr = np.array([corr[1, 0], corr[2, 0], corr[2, 1]], dtype=float)
        val = tvtl(nu, upp, cr, algo.eps)
        err = algo.eps
    else:
        raise ValueError("need n = 2 or 3 for TVPACK() algorithm")
    return val, err, 0


def _probval(algorithm, n, df, lower, upper, infin, corr, delta):
    if isinstance(algorithm, GenzBretz):
        return probval_genzbretz(algorithm, n, df, lower, upper, infin, corr, delta)
    if isinstance(algorithm, Miwa):
        return probval_miwa(algorithm, n, df, lower, upper, infin, corr, delta)
    if isinstance(algorithm, TVPACK):
        return probval_tvpack(algorithm, n, df, lower, upper, infin, corr, delta)
    raise TypeError("algorithm is not GenzBretz, Miwa, or TVPACK")


def mvt(lower, upper, df, corr, delta, algorithm=None):
    if algorithm is None:
        algorithm = GenzBretz()
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    delta = np.asarray(delta, dtype=float)
    corr = np.asarray(corr, dtype=float)
    close = np.abs(lower - upper) < _SQRT_EPS * (np.abs(lower) + np.abs(upper))
    if np.any(close | (lower == upper)):
        return {"value": 0.0, "error": 0.0, "msg": "lower == upper", "algorithm": algorithm.__class__.__name__}
    n = corr.shape[1] if corr.ndim == 2 else None
    if n is None or n < 2:
        raise ValueError("dimension less then n = 2")
    if len(lower) != n or len(upper) != n:
        raise ValueError("wrong dimensions")
    if n > 1000:
        raise ValueError("only dimensions 1 <= n <= 1000 allowed")
    infin = _infin(lower, upper)
    if n >= 2 and isinstance(algorithm, (Miwa, TVPACK)):
        if np.any(infin == -1):
            keep = infin != -1
            n = int(np.sum(keep))
            corr = corr[np.ix_(keep, keep)]
            upper = upper[keep]
            lower = lower[keep]
            delta = delta[keep]
            if n <= 1:
                if n:
                    upper = upper - delta
                    lower = lower - delta
                value = 1.0 if n == 0 else pnorm(float(upper[0])) - pnorm(float(lower[0]))
                return {
                    "value": value,
                    "error": 0.0,
                    "msg": "Normal Complettion (dim reduced to 1)",
                    "algorithm": algorithm.__class__.__name__,
                }
            infin = infin[keep]
        if isinstance(algorithm, Miwa) and np.any(infin == 0):
            where = infin == 0
            sign = np.ones(n)
            sign[where] = -1.0
            corr = sign[:, None] * corr * sign[None, :]
            infin = infin.copy()
            infin[where] = 1
            saved = upper[where].copy()
            upper = upper.copy()
            lower = lower.copy()
            upper[where] = -lower[where]
            lower[where] = -saved
    if np.all(infin < 0):
        return {"value": 1.0, "error": 0.0, "msg": "Normal Completion", "algorithm": algorithm.__class__.__name__}
    packed = corr
    if isinstance(algorithm, GenzBretz) and n > 1:
        packed = pack_corr(corr)
    value, error, inform = _probval(algorithm, n, df, lower, upper, infin, packed, delta)
    return {"value": value, "error": error, "msg": _messages(inform), "algorithm": algorithm.__class__.__name__}


def pmvnorm(lower=-math.inf, upper=math.inf, mean=None, corr=None, sigma=None, algorithm=None, keepAttr=True, seed=None):
    """R pmvnorm. seed selects the uniforms inside GenzBretz and is restored afterwards."""
    state = _with_seed(seed)
    try:
        if algorithm is None:
            algorithm = GenzBretz()
        if mean is None:
            mean = np.zeros(len(_as_1d(lower)))
        carg = checkmvArgs(lower, upper, mean, corr, sigma)
        if carg["corr"] is not None:
            if carg["uni"]:
                raise ValueError(f"{_quote('sigma')} not specified: cannot compute pnorm")
            low = carg["lower"] - carg["mean"]
            upp = carg["upper"] - carg["mean"]
            center = np.zeros(len(low))
            ret = mvt(low, upp, 0, carg["corr"], center, algorithm)
        elif carg["uni"]:
            sd = math.sqrt(carg["sigma"])
            value = pnorm(float(carg["upper"][0]), mean=float(carg["mean"][0]), sd=sd) - pnorm(
                float(carg["lower"][0]), mean=float(carg["mean"][0]), sd=sd
            )
            ret = {"value": value, "error": 0.0, "msg": "univariate: using pnorm", "algorithm": algorithm.__class__.__name__}
        else:
            scale = np.sqrt(np.diag(carg["sigma"]))
            low = (carg["lower"] - carg["mean"]) / scale
            upp = (carg["upper"] - carg["mean"]) / scale
            center = np.zeros(len(low))
            ret = mvt(low, upp, 0, _cov2cor(carg["sigma"]), center, algorithm)
        if keepAttr:
            return Prob(ret["value"], ret["error"], ret["msg"], ret["algorithm"])
        return float(ret["value"])
    finally:
        if seed is not None:
            _restore(state)


def pmvt(lower=-math.inf, upper=math.inf, delta=None, df=1, corr=None, sigma=None, algorithm=None, type="shifted", keepAttr=True, seed=None):
    """R pmvt. Integer df, and df 0 is the normal probability."""
    state = _with_seed(seed)
    try:
        if algorithm is None:
            algorithm = GenzBretz()
        if delta is None:
            delta = np.zeros(len(_as_1d(lower)))
        kind = match_arg(type, ("Kshirsagar", "shifted"))
        carg = checkmvArgs(lower, upper, delta, corr, sigma)
        if kind == "shifted":
            if carg["corr"] is not None:
                d = 1.0
            elif carg["sigma"] is not None:
                if carg["uni"]:
                    d = math.sqrt(carg["sigma"])
                else:
                    d = np.sqrt(np.diag(carg["sigma"]))
                    carg["corr"] = _cov2cor(carg["sigma"])
                    carg["sigma"] = None
            else:
                d = 1.0
            carg["lower"] = (carg["lower"] - carg["mean"]) / d
            carg["upper"] = (carg["upper"] - carg["mean"]) / d
            carg["mean"] = np.zeros(len(carg["mean"]))
        if df is None:
            raise ValueError(f"{_quote('df')} not specified")
        df = float(np.ravel(np.asarray(df, dtype=float))[0])
        if df < 0:
            raise ValueError(f"cannot compute multivariate t distribution with {_quote('df')} < 0")
        if math.isfinite(df) and df != int(df):
            raise ValueError(f"{_quote('df')} is not an integer")
        if carg["uni"]:
            if carg["sigma"] is not None:
                carg["upper"] = carg["upper"] / math.sqrt(carg["sigma"])
                carg["lower"] = carg["lower"] / math.sqrt(carg["sigma"])
            if df > 0:
                value = _pt_ncp(float(carg["upper"][0]), df, float(carg["mean"][0])) - _pt_ncp(
                    float(carg["lower"][0]), df, float(carg["mean"][0])
                )
                msg = "univariate: using pt"
            else:
                value = pnorm(float(carg["upper"][0]), mean=float(carg["mean"][0])) - pnorm(
                    float(carg["lower"][0]), mean=float(carg["mean"][0])
                )
                msg = "univariate: using pnorm"
            ret = {"value": value, "error": 0.0, "msg": msg, "algorithm": algorithm.__class__.__name__}
        elif carg["corr"] is not None:
            ret = mvt(carg["lower"], carg["upper"], df, carg["corr"], carg["mean"], algorithm)
        else:
            d = np.sqrt(np.diag(carg["sigma"]))
            ret = mvt(carg["lower"] / d, carg["upper"] / d, df, _cov2cor(carg["sigma"]), carg["mean"] / d, algorithm)
        if keepAttr:
            return Prob(ret["value"], ret["error"], ret["msg"], ret["algorithm"])
        return float(ret["value"])
    finally:
        if seed is not None:
            _restore(state)


def _pt_ncp(x, df, ncp):
    if ncp == 0:
        return pt(x, df)
    return float(nct.cdf(x, df, ncp))


def _qt_ncp(p, df, ncp=0.0):
    if not math.isfinite(df):
        from extradistr._rng import qnorm

        return qnorm(p)
    if ncp == 0:
        return qt(p, df)
    return float(nct.ppf(p, df, ncp))
