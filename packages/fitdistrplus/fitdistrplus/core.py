"""Numerical Python translation of the public fitdistrplus helpers.

The functions deliberately return plain dictionaries/arrays: R's S3 classes are
presentation machinery, while these are the values consumed by callers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np
from scipy import optimize, stats


_DIST = {
    "norm": stats.norm, "lnorm": stats.lognorm, "exp": stats.expon,
    "gamma": stats.gamma, "weibull": stats.weibull_min, "logis": stats.logistic,
    "unif": stats.uniform, "beta": stats.beta, "pois": stats.poisson,
    "nbinom": stats.nbinom, "geom": stats.geom,
}


def _dist(name, params):
    if callable(name):
        return name
    try:
        d = _DIST[name]
    except KeyError as exc:
        raise ValueError(f"unsupported scipy distribution {name!r}") from exc
    p = dict(params or {})
    # R's dlnorm uses meanlog/sdlog; scipy uses shape, loc, scale.
    if name == "lnorm":
        return d(s=p.get("sdlog", p.get("s", 1)), scale=np.exp(p.get("meanlog", 0)),
                 loc=p.get("loc", 0))
    if name == "exp":
        return d(scale=1 / p["rate"] if "rate" in p else p.get("scale", 1),
                 loc=p.get("loc", 0))
    if name == "gamma":
        return d(a=p.get("shape", 1), scale=1 / p["rate"] if "rate" in p
                 else p.get("scale", 1), loc=p.get("loc", 0))
    if name == "weibull":
        return d(c=p.get("shape", 1), scale=p.get("scale", 1), loc=p.get("loc", 0))
    if name == "norm":
        return d(loc=p.get("mean", p.get("loc", 0)),
                 scale=p.get("sd", p.get("scale", 1)))
    if name == "unif":
        lo = p.get("min", p.get("loc", 0))
        hi = p.get("max", lo + p.get("scale", 1))
        return d(loc=lo, scale=hi - lo)
    if name == "logis":
        return d(loc=p.get("location", p.get("loc", 0)),
                 scale=p.get("scale", 1))
    if name in ("pois", "geom"):
        return d(mu=p.get("lambda", p.get("mu", 1))) if name == "pois" else d(
            p.get("prob", 0.5))
    if name == "nbinom":
        return d(n=p.get("size", 1), p=p.get("prob", 0.5))
    return d(**p)


def _default_start(name, x):
    x = np.asarray(x, float)
    if name == "norm": return {"mean": float(np.mean(x)), "sd": float(np.std(x))}
    if name == "exp": return {"rate": float(1 / np.mean(x))}
    if name == "gamma":
        m, v = np.mean(x), np.var(x, ddof=0)
        return {"shape": max(m * m / v, .1), "rate": max(m / v, 1e-8)}
    if name == "lnorm":
        z = np.log(x[x > 0])
        return {"meanlog": float(np.mean(z)), "sdlog": float(np.std(z))}
    if name == "weibull": return {"shape": 1.0, "scale": float(np.mean(x))}
    if name == "unif": return {"min": float(np.min(x)), "max": float(np.max(x))}
    return {"loc": float(np.mean(x)), "scale": float(np.std(x) or 1)}


def fitdist(data, distr, method="mle", start=None, fix_arg=None, discrete=None,
            keepdata=True, keepdata_nb=100, calcvcov=True, **kwargs):
    """Fit an uncensored distribution using scipy's bounded L-BFGS-B path.

    Positive parameters are optimized on the log scale, which is the stable
    analogue of R's parameter checks.  ``convergence`` is scipy's status code.
    """
    x = np.asarray(data, dtype=float).ravel()
    if x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("data must contain at least two finite values")
    fixed = dict(fix_arg or {})
    initial = dict(_default_start(distr, x) if start is None else start)
    names = [k for k in initial if k not in fixed]
    vals = np.array([initial[k] for k in names], float)
    positive = {"sd", "sdlog", "rate", "shape", "scale", "prob", "lambda", "size"}
    logmask = np.array([k in positive for k in names])
    z0 = np.where(logmask, np.log(np.maximum(vals, 1e-12)), vals)

    def unpack(z):
        q = fixed.copy()
        q.update({k: (float(np.exp(v)) if lm else float(v))
                  for k, v, lm in zip(names, z, logmask)})
        return q

    def objective(z):
        p = unpack(z)
        try:
            d = _dist(distr, p)
            y = d.logpmf(x) if discrete else d.logpdf(x)
            return float(-np.sum(y)) if np.all(np.isfinite(y)) else 1e300
        except (ValueError, TypeError, FloatingPointError):
            return 1e300

    if method != "mle":
        raise NotImplementedError("only method='mle' is implemented in this batch")
    result = optimize.minimize(objective, z0, method="L-BFGS-B",
                               options={"ftol": 1e-15, "gtol": 1e-8, "maxiter": 10000})
    estimate = unpack(result.x)
    loglik = -float(result.fun)
    npar = len(names)
    out = {"estimate": estimate, "method": method, "loglik": loglik,
           "aic": 2 * (npar - loglik), "bic": 2 * (-loglik) + np.log(x.size) * npar,
           "n": int(x.size), "distname": distr, "fix.arg": fixed or None,
           "convergence": int(result.status), "discrete": bool(discrete),
           "data": x if keepdata else x[:min(keepdata_nb, x.size)]}
    if calcvcov and result.hess_inv is not None:
        try:
            h = np.asarray(result.hess_inv.todense())
            scale = np.exp(result.x) if np.any(logmask) else np.ones(npar)
            out["vcov"] = h * np.outer(scale, scale)
            out["sd"] = np.sqrt(np.maximum(np.diag(out["vcov"]), 0))
        except Exception:
            out["vcov"] = out["sd"] = None
    else:
        out["vcov"] = out["sd"] = None
    return out


def fitdistcens(censdata, distr, start=None, fix_arg=None, keepdata=True,
                keepdata_nb=100, calcvcov=True, **kwargs):
    left = np.asarray(censdata["left"], float)
    right = np.asarray(censdata["right"], float)
    if left.size < 2 or left.size != right.size:
        raise ValueError("censdata must have left and right columns")
    fixed = dict(fix_arg or {})
    init = dict(_default_start(distr, np.where(np.isfinite(right), (left + right) / 2, left))
                if start is None else start)
    names = [k for k in init if k not in fixed]
    positive = {"sd", "sdlog", "rate", "shape", "scale"}
    lm = np.array([k in positive for k in names])
    z0 = np.array([np.log(max(init[k], 1e-12)) if m else init[k]
                   for k, m in zip(names, lm)], float)
    def unpack(z):
        p = fixed.copy()
        p.update({k: float(np.exp(v)) if m else float(v)
                  for k, v, m in zip(names, z, lm)})
        return p
    def objective(z):
        d = _dist(distr, unpack(z))
        pl = d.cdf(left)
        pr = np.where(np.isfinite(right), d.cdf(right), 1.0)
        # exact, left-, right-, and interval-censored observations
        ll = np.where(left == right, d.pdf(left), pr - pl)
        return float(-np.sum(np.log(np.maximum(ll, np.finfo(float).tiny))))
    result = optimize.minimize(objective, z0, method="L-BFGS-B",
                               options={"ftol": 1e-15, "gtol": 1e-8, "maxiter": 10000})
    est = unpack(result.x); ll = -float(result.fun); n = left.size; k = len(names)
    return {"estimate": est, "method": "mle", "loglik": ll, "aic": -2*ll+2*k,
            "bic": -2*ll+np.log(n)*k, "n": int(n), "distname": distr,
            "fix.arg": fixed or None, "convergence": int(result.status),
            "censdata": {"left": left, "right": right}}


def descdist(data, discrete=False, boot=None, method="unbiased", graph=True, print=True, **kwargs):
    x = np.asarray(data, float)
    n = x.size; m = x.mean(); centered = x - m
    var = np.mean(centered**2)
    sd = np.sqrt(var) if method == "sample" else np.std(x, ddof=1)
    g1 = np.mean(centered**3) / var**1.5
    g2 = np.mean(centered**4) / var**2
    if method == "unbiased":
        skew = np.sqrt(n*(n-1))*g1/(n-2)
        kurt = (n-1)/((n-2)*(n-3))*((n+1)*g2-3*(n-1))+3
    elif method == "sample": skew, kurt = g1, g2
    else: raise ValueError("method must be 'unbiased' or 'sample'")
    return {"min": float(x.min()), "max": float(x.max()), "median": float(np.median(x)),
            "mean": float(m), "sd": float(sd), "skewness": float(skew),
            "kurtosis": float(kurt), "method": method}


def detectbound(distname, vstart, obs, fix_arg=None, echo=False):
    p = dict(vstart); fixed = set((fix_arg or {}).keys()); names = [k for k in p if k not in fixed]
    lo, hi = {}, {}; eps = np.sqrt(np.finfo(float).eps)
    for name in names:
        lo[name], hi[name] = -np.inf, np.inf
        for a in (-1., 0., 1.):
            q = dict(p); q[name] = a-eps
            q2 = dict(p); q2[name] = a+eps
            try: ok1 = np.all(np.isfinite(_dist(distname, q).pdf(obs)))
            except Exception: ok1 = False
            try: ok2 = np.all(np.isfinite(_dist(distname, q2).pdf(obs)))
            except Exception: ok2 = False
            if not ok1 and ok2: lo[name] = a
            if ok1 and not ok2: hi[name] = a
    return np.array([list(lo.values()), list(hi.values())]) if names else None


def gofstat(f, chisqbreaks=None, meancount=None, discrete=None, fitnames=None):
    fits = f if isinstance(f, (list, tuple)) else [f]
    out = {"aic": np.array([z["aic"] for z in fits]), "bic": np.array([z["bic"] for z in fits]),
           "nbfit": len(fits)}
    if discrete is None: discrete = fits[0].get("discrete", False)
    if not discrete:
        x = np.sort(np.asarray(fits[0]["data"])); n = x.size
        d = _dist(fits[0]["distname"], fits[0]["estimate"])
        u = d.cdf(x); i = np.arange(1, n+1)
        out.update(ks=float(np.max(np.maximum(np.abs(u-i/n), np.abs(u-(i-1)/n)))),
                   cvm=float(1/(12*n)+np.sum((u-(2*i-1)/(2*n))**2)),
                   ad=float(-n-np.mean((2*i-1)*(np.log(u)+np.log(1-u)))))
    return out


def _compare_plot(x, fits, kind="cdf", **kwargs):
    import matplotlib.pyplot as plt
    ax = kwargs.pop("ax", None) or plt.subplots()[1]
    x = np.asarray(x, float)
    for name, para in fits.items() if isinstance(fits, Mapping) else fits:
        d = _dist(name, para)
        y = d.cdf(x) if kind == "cdf" else d.pdf(x)
        ax.plot(x, y, label=name)
    return ax


def cdfcomp(data, fits, **kwargs): return _compare_plot(data, fits, "cdf", **kwargs)
def cdfcompcens(censdata, fits, **kwargs):
    x = np.sort(np.unique(np.r_[censdata["left"], censdata["right"]]))
    return _compare_plot(x, fits, "cdf", **kwargs)
def denscomp(data, fits, **kwargs): return _compare_plot(data, fits, "dens", **kwargs)
def CIcdfplot(*args, **kwargs): return cdfcomp(*args, **kwargs)


def Surv2fitdistcens(time, status):
    t, s = np.asarray(time, float), np.asarray(status, int)
    return {"left": t, "right": np.where(s == 1, t, np.inf)}


def bootdist(f, niter=1001, **kwargs):
    x = np.asarray(f["data"]); vals = []
    for _ in range(int(niter)):
        vals.append(list(fitdist(np.random.choice(x, x.size, replace=True), f["distname"],
                                  start=f["estimate"], fix_arg=f.get("fix.arg"),
                                  discrete=f.get("discrete", False))["estimate"].values()))
    return {"estim": np.asarray(vals), "fit": f}


def bootdistcens(f, niter=1001, **kwargs):
    cd = f["censdata"]; vals = []
    for _ in range(int(niter)):
        ix = np.random.randint(len(cd["left"]), size=len(cd["left"]))
        vals.append(list(fitdistcens({"left": cd["left"][ix], "right": cd["right"][ix]},
                                     f["distname"], start=f["estimate"])["estimate"].values()))
    return {"estim": np.asarray(vals), "fit": f}
