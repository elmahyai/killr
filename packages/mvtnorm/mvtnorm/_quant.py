"""Equicoordinate quantiles. The local linear step is R's quasi glm."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import cauchy

from extradistr._rng import qnorm
from extradistr._special import pnorm, pt, qt

from mvtnorm._prob import Prob, _pt_ncp, _qt_ncp, checkmvArgs, pmvnorm, pmvt

_XMAX = float(np.finfo(float).max)
_TOL = float(np.finfo(float).eps) ** 0.25


def _sign(x):
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0


def _zeroin(f, lower, upper, f_lower, f_upper, tol=_TOL, maxiter=1000):
    """Brent's zeroin, the root R's C_zeroin2 returns."""
    a, b = float(lower), float(upper)
    fa, fb = float(f_lower), float(f_upper)
    c, fc = a, fa
    d = e = b - a
    for it in range(1, maxiter + 1):
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol1 = 2.0 * float(np.finfo(float).eps) * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)
        if abs(xm) <= tol1 or fb == 0.0:
            return b, it, abs(xm)
        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0:
                q = -q
            p = abs(p)
            min1 = 3.0 * xm * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < (min1 if min1 < min2 else min2):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d
        a, fa = b, fb
        if abs(d) > tol1:
            b += d
        else:
            b += math.copysign(tol1, xm)
        fb = float(f(b))
    return b, -maxiter, abs(b - a)


def uniroot(f, interval, extend_int="yes", tol=_TOL, maxiter=1000):
    lower, upper = float(interval[0]), float(interval[1])
    if lower >= upper:
        raise ValueError("lower < upper  is not fulfilled")
    f_lower = float(f(lower))
    f_upper = float(f(upper))
    if math.isnan(f_lower) or math.isnan(f_upper):
        raise ValueError("f() at an endpoint is NA")

    def truncate(x):
        return min(max(x, -_XMAX), _XMAX)

    do_x = f_lower * f_upper > 0 if extend_int == "yes" else False
    it = 0
    if do_x:

        def delta(u):
            return 0.01 * max(1e-4, abs(u))

        step = [delta(lower), delta(upper)]
        while f_lower * f_upper > 0 and (math.isfinite(lower) or math.isfinite(upper)):
            it += 1
            if it > maxiter:
                raise RuntimeError(f"no sign change found in {it - 1} iterations")
            if math.isfinite(lower):
                old_l, old_f = lower, f_lower
                lower = lower - step[0]
                f_lower = float(f(lower))
                if math.isnan(f_lower):
                    lower, f_lower = old_l, old_f
                    step[0] /= 4
            if math.isfinite(upper):
                old_u, old_f = upper, f_upper
                upper = upper + step[1]
                f_upper = float(f(upper))
                if math.isnan(f_upper):
                    upper, f_upper = old_u, old_f
                    step[1] /= 4
            step[0] *= 2
            step[1] *= 2
    if _sign(f_lower) * _sign(f_upper) > 0:
        raise ValueError("f() values at end points not of opposite sign")
    root, _iters, _prec = _zeroin(f, lower, upper, truncate(f_lower), truncate(f_upper), tol, maxiter)
    return root


def _dnorm(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


class _Fit:
    def __init__(self, coef, dispersion, df_residual, weights, x):
        self.coef = np.asarray(coef, dtype=float)
        self.dispersion = float(dispersion)
        self.df_residual = df_residual
        self.weights = np.asarray(weights, dtype=float)
        self.x = np.asarray(x, dtype=float)
        xtw = self.x.T * self.weights
        self.cov_unscaled = np.linalg.inv(xtw @ self.x)


def _link(name, y):
    y = np.asarray(y, dtype=float)
    if name == "probit":
        return np.vectorize(qnorm)(y), np.vectorize(lambda e: pnorm(e)), _dnorm
    return (
        np.vectorize(lambda p: float(cauchy_ppf(p)))(y),
        np.vectorize(lambda e: float(cauchy_cdf(e))),
        lambda e: 1.0 / (math.pi * (1.0 + e * e)),
    )


def cauchy_cdf(x):
    return float(cauchy.cdf(x))


def cauchy_ppf(p):
    return float(cauchy.ppf(p))


def fitlr(x, y, weights, link):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.asarray(weights, dtype=float)
    keep = weights > 0
    x, y, weights = x[keep], y[keep], weights[keep]
    design = np.column_stack([np.ones(len(x)), x])
    eta = np.array([qnorm(float(v)) if link == "probit" else cauchy_ppf(float(v)) for v in y])
    mu_of = pnorm if link == "probit" else cauchy_cdf
    dmu_of = _dnorm if link == "probit" else (lambda e: 1.0 / (math.pi * (1.0 + e * e)))
    wls_w = weights
    for _ in range(50):
        mu = np.array([mu_of(float(e)) for e in eta])
        dmu = np.array([dmu_of(float(e)) for e in eta])
        wls_w = weights * dmu ** 2
        z = eta + (y - mu) / dmu
        xtw = design.T * wls_w
        coef = np.linalg.solve(xtw @ design, xtw @ z)
        eta_new = design @ coef
        if np.max(np.abs(eta_new - eta)) < 1e-12:
            eta = eta_new
            break
        eta = eta_new
    mu = np.array([mu_of(float(e)) for e in eta])
    dmu = np.array([dmu_of(float(e)) for e in eta])
    pearson = np.sum(weights * (y - mu) ** 2)
    df = max(len(y) - 2, 1)
    dispersion = pearson / df
    return _Fit(coef, dispersion, len(y) - 2, wls_w, design)


def _predict(fit, x, se=False):
    x = np.atleast_1d(np.asarray(x, dtype=float))
    design = np.column_stack([np.ones(len(x)), x])
    eta = design @ fit.coef
    if not se:
        return eta
    se_fit = np.sqrt(np.sum((design @ fit.cov_unscaled) * design, axis=1) * fit.dispersion)
    return eta, se_fit


def _wgts(typred, ttarg):
    dists = np.abs(np.asarray(typred) - ttarg)
    if np.sum((dists < 1) & (dists > 0.0001)) < 3:
        return np.ones(len(typred))
    return (1 - dists ** 3) ** 3 * (dists < 1)


def _sanitize_x(x, minx):
    return np.maximum(np.asarray(x, dtype=float), minx)


def _sanitize_y(y):
    eps = float(np.finfo(float).eps)
    y = np.asarray(y, dtype=float)
    return np.minimum(np.maximum(y, eps), 1 - eps)


def get_int(p, delta, sigma, tail, type="Kshirsagar", df=math.inf):
    sigma = np.asarray(sigma, dtype=float)
    if sigma.ndim == 1:
        sigma = np.diag(sigma)
    sds = np.sqrt(np.diag(sigma))
    delta = np.broadcast_to(np.asarray(delta, dtype=float), sds.shape).astype(float)
    if df == 0 or not math.isfinite(df):
        df = math.inf

        def cdf(x, lower_tail=True):
            z = (x - delta) / sds
            vals = np.array([pnorm(float(v)) for v in z])
            return vals if lower_tail else 1 - vals
    elif type == "shifted":

        def cdf(x, lower_tail=True):
            z = (x - delta) / sds
            vals = np.array([pt(float(v), df) for v in z])
            return vals if lower_tail else 1 - vals
    else:

        def cdf(x, lower_tail=True):
            vals = np.array([_pt_ncp(float(v), df, float(n)) for v, n in zip(np.broadcast_to(x, sds.shape), delta / sds)])
            return vals if lower_tail else 1 - vals

    if tail == "both.tails":
        interval = (0.0, 10.0)

        def func(x):
            return float(np.prod(cdf(x) - cdf(-x)) - p)

        ub = np.max(np.abs(delta + sds * _qt_ncp(1 - (1 - p) / 2, df)))
    elif tail == "upper.tail":
        interval = (-10.0, 10.0)

        def func(x):
            return float(np.prod(cdf(x, lower_tail=False)) - p)

        ub = np.min(delta + sds * _qt_ncp(1 - p, df))
    else:
        interval = (-10.0, 10.0)

        def func(x):
            return float(np.prod(cdf(x)) - p)

        ub = np.max(delta + sds * _qt_ncp(p, df))
    lb = uniroot(func, interval, extend_int="yes")
    return np.sort([lb, ub])


def get_quant_loclin(func, targ, interval, ptol=0.005, maxiter=500, link="probit", minx=-math.inf):
    if interval[1] <= interval[0]:
        raise ValueError("first entry of interval needs to be smaller than second")
    x = np.zeros(4 + maxiter)
    y = np.zeros(4 + maxiter)
    xest = np.zeros(1 + maxiter)
    x[:3] = _sanitize_x([interval[0], interval[1], 0.5 * (interval[0] + interval[1])], minx)
    res = [func(float(v)) for v in x[:3]]
    msg = getattr(res[0], "msg", None)
    if msg == "Covariance matrix not positive semidefinite":
        raise ValueError("Covariance matrix not positive semidefinite")
    if float(res[0]) > float(res[1]):
        raise ValueError("func does not appear to be monotone")
    y[:3] = _sanitize_y([float(v) for v in res])
    quf = qnorm if link == "probit" else cauchy_ppf
    cdf = pnorm if link == "probit" else cauchy_cdf
    ttarg = quf(targ)
    fit = fitlr(x[:3], y[:3], np.ones(3), link)
    xest[0] = (ttarg - fit.coef[0]) / fit.coef[1]
    x[3] = float(_sanitize_x([xest[0]], minx)[0])
    y[3] = float(_sanitize_y([float(func(x[3]))])[0])
    count = 4
    i = 1
    for i in range(1, maxiter + 1):
        xcur = x[:count]
        ycur = y[:count]
        pred = _predict(fit, xcur)
        weights = _wgts(pred, ttarg)
        fit = fitlr(xcur, ycur, weights, link)
        eta, se = _predict(fit, [xest[i - 1]], se=True)
        crit = qt(1 - 0.05 / 2, fit.df_residual) if fit.df_residual > 0 else math.inf
        stop = (eta[0] + crit * se[0] < ttarg + ptol) and (eta[0] - crit * se[0] > ttarg - ptol)
        if stop:
            break
        xest[i] = (ttarg - fit.coef[0]) / fit.coef[1]
        new_x = _new_points(fit, xest[i])
        new_x = _sanitize_x(new_x, minx)
        new_y = _sanitize_y([float(func(float(v))) for v in new_x])
        x[count : count + 2] = new_x
        y[count : count + 2] = new_y
        count += 2
    f_quant = float(_predict(fit, [xest[i - 1]])[0])
    out = Prob(xest[i - 1], msg="Normal Completion" if i < maxiter else "Maximum number of iterations reached without sufficient accuracy")
    return {"quantile": float(xest[i - 1]), "f.quantile": float(cdf(f_quant)), "message": out.msg}


def _new_points(fit, xest):
    eta, se = _predict(fit, [xest], se=True)
    x_lb = (eta[0] - se[0] - fit.coef[0]) / fit.coef[1]
    x_ub = (eta[0] + se[0] - fit.coef[0]) / fit.coef[1]
    return np.array([x_lb, x_ub])


def qmvnorm(p, interval=None, tail="lower.tail", mean=0, corr=None, sigma=None, algorithm=None, ptol=0.001, maxiter=500, trace=False, seed=None):
    from mvtnorm._prob import GenzBretz, _restore, _rng_state, _with_seed

    state = _with_seed(seed)
    try:
        p = float(p)
        if not 0 <= p <= 1:
            raise ValueError("'p' is not a double between zero and one")
        if algorithm is None:
            algorithm = GenzBretz()
        tail = __import__("mvtnorm._dens", fromlist=["match_arg"]).match_arg(tail, ("lower.tail", "upper.tail", "both.tails"))
        if tail == "both.tails" and p < 0.5:
            raise ValueError("cannot compute two-sided quantile for p < 0.5")
        dim = 1
        if corr is not None and np.ndim(corr) == 2:
            dim = len(corr)
        if sigma is not None and np.ndim(sigma) == 2:
            dim = len(sigma)
        args = checkmvArgs(np.zeros(dim), np.zeros(dim), mean, corr, sigma)
        if args["uni"]:
            if args["sigma"] is None:
                raise ValueError("'sigma' not specified: cannot compute qnorm")
            pp = p
            if tail == "both.tails":
                pp = p / 2 if p < 0.5 else 1 - (1 - p) / 2
            sd = math.sqrt(float(args["sigma"]))
            z = qnorm(pp if tail != "upper.tail" else 1 - pp)
            return {"quantile": float(args["mean"][0]) + sd * z, "f.quantile": pp}
        dim = len(args["mean"])
        frozen = _rng_state()

        def pfct(q):
            _restore(frozen)
            q = abs(q) if tail == "both.tails" else q
            if tail == "both.tails":
                low, upp = np.full(dim, -abs(q)), np.full(dim, abs(q))
            elif tail == "upper.tail":
                low, upp = np.full(dim, q), np.full(dim, math.inf)
            else:
                low, upp = np.full(dim, -math.inf), np.full(dim, q)
            ret = pmvnorm(low, upp, args["mean"], args["corr"], args["sigma"], algorithm)
            if tail == "upper.tail":
                return Prob(1 - float(ret), ret.error, ret.msg, ret.algorithm)
            return ret

        if interval is None:
            sig = args["corr"] if args["sigma"] is None else args["sigma"]
            interval = get_int(p, args["mean"], sig, tail, df=math.inf)
            dif = interval[1] - interval[0]
            interval = interval + np.array([-1, 1]) * 0.2 * max(dif, 0.1)
        target = 1 - p if tail == "upper.tail" else p
        minx = 0 if tail == "both.tails" else -math.inf
        qroot = get_quant_loclin(pfct, target, interval, ptol=ptol, maxiter=maxiter, link="probit", minx=minx)
        qroot["f.quantile"] = qroot["f.quantile"] - target
        return qroot
    finally:
        if seed is not None:
            _restore(state)


def qmvt(p, interval=None, tail="lower.tail", df=1, delta=0, corr=None, sigma=None, algorithm=None, type="shifted", ptol=0.001, maxiter=500, trace=False, seed=None):
    from mvtnorm._dens import match_arg
    from mvtnorm._prob import GenzBretz, _restore, _rng_state, _with_seed

    state = _with_seed(seed)
    try:
        p = float(p)
        if not 0 < p < 1:
            raise ValueError("'p' is not a double between zero and one")
        if algorithm is None:
            algorithm = GenzBretz()
        type = match_arg(type, ("Kshirsagar", "shifted"))
        tail = match_arg(tail, ("lower.tail", "upper.tail", "both.tails"))
        if tail == "both.tails" and p < 0.5:
            raise ValueError("cannot compute two-sided quantile for p < 0.5")
        dim = 1
        if corr is not None and np.ndim(corr) >= 1:
            dim = int(np.shape(corr)[0])
        if sigma is not None and np.ndim(sigma) >= 1:
            dim = int(np.shape(sigma)[0])
        args = checkmvArgs(np.zeros(dim), np.zeros(dim), delta, corr, sigma)
        if args["uni"]:
            if args["sigma"] is None:
                args["sigma"] = 1
            if not math.isclose(float(args["sigma"]), 1.0):
                raise ValueError("sigma != 1 not implemented for univariate case")
            pp = p
            if tail == "both.tails":
                pp = p / 2 if p < 0.5 else 1 - (1 - p) / 2
            if df == 0 or not math.isfinite(df):
                q = qnorm(pp if tail != "upper.tail" else 1 - pp) + float(args["mean"][0])
            else:
                q = _qt_ncp(pp if tail != "upper.tail" else 1 - pp, df, float(args["mean"][0]))
            return {"quantile": q, "f.quantile": pp}
        dim = len(args["mean"])
        frozen = _rng_state()

        def pfct(q):
            _restore(frozen)
            if tail == "both.tails":
                low, upp = np.full(dim, -abs(q)), np.full(dim, abs(q))
            elif tail == "upper.tail":
                low, upp = np.full(dim, q), np.full(dim, math.inf)
            else:
                low, upp = np.full(dim, -math.inf), np.full(dim, q)
            ret = pmvt(low, upp, args["mean"], df, args["corr"], args["sigma"], algorithm, type)
            if tail == "upper.tail":
                return Prob(1 - float(ret), getattr(ret, "error", None), getattr(ret, "msg", None), getattr(ret, "algorithm", None))
            return ret

        if interval is None:
            sig = args["corr"] if args["sigma"] is None else args["sigma"]
            interval = get_int(p, args["mean"], sig, tail, type=type, df=df)
            dif = float(interval[1] - interval[0])
            interval = interval + np.array([-1.0, 1.0]) * 0.2 * max(dif, 0.1)
        target = 1 - p if tail == "upper.tail" else p
        link = "cauchit" if 0 < df <= 7 else "probit"
        minx = 0 if tail == "both.tails" else -math.inf
        qroot = get_quant_loclin(pfct, target, interval, ptol=ptol, maxiter=maxiter, link=link, minx=minx)
        qroot["f.quantile"] = qroot["f.quantile"] - target
        return qroot
    finally:
        if seed is not None:
            _restore(state)
