"""Numerical and comparison helpers for fitdistrplus translation batch.

The plotting routines deliberately return the values used to draw the plot.
This keeps the API useful in non-interactive Python programs and makes the
translation testable independently of Matplotlib's rendering.
"""
from __future__ import annotations

import itertools
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy import optimize, stats


_DIST = {
    "norm": stats.norm, "normal": stats.norm, "lnorm": stats.lognorm,
    "lognormal": stats.lognorm, "exp": stats.expon, "gamma": stats.gamma,
    "weibull": stats.weibull_min, "weibull_min": stats.weibull_min,
    "unif": stats.uniform, "uniform": stats.uniform, "logis": stats.logistic,
    "logistic": stats.logistic, "cauchy": stats.cauchy, "chisq": stats.chi2,
    "beta": stats.beta, "geom": stats.geom, "pois": stats.poisson,
    "binom": stats.binom, "nbinom": stats.nbinom,
}


def _asdict(para: Any, names: Sequence[str] | None = None) -> dict[str, float]:
    if para is None:
        return {}
    if isinstance(para, Mapping):
        return {str(k): float(v) for k, v in para.items()}
    a = np.asarray(para, dtype=float).ravel()
    if names is None:
        names = ("mean", "sd") if len(a) == 2 else tuple(f"p{i}" for i in range(len(a)))
    return dict(zip(names, a))


def _rv(distr: str, para: Any):
    name = str(distr).lower()
    if name not in _DIST:
        raise ValueError(f"unknown distribution: {distr}")
    d = _DIST[name]
    p = _asdict(para)
    if name in ("norm", "normal"):
        return d(loc=p.get("mean", p.get("loc", 0)), scale=p.get("sd", p.get("scale", 1)))
    if name in ("exp",):
        return d(loc=p.get("min", p.get("loc", 0)), scale=p.get("rate", p.get("scale", 1)))
    if name in ("unif", "uniform"):
        return d(loc=p.get("min", p.get("loc", 0)), scale=p.get("max", p.get("scale", 1))-p.get("min", p.get("loc", 0)))
    if name in ("lnorm", "lognormal"):
        return d(s=p.get("sdlog", p.get("s", 1)), scale=np.exp(p.get("meanlog", np.log(p.get("scale", 1)))), loc=p.get("min", p.get("loc", 0)))
    if name in ("weibull", "weibull_min"):
        return d(c=p.get("shape", p.get("c", 1)), scale=p.get("scale", 1), loc=p.get("loc", 0))
    if name == "gamma":
        return d(a=p.get("shape", p.get("a", 1)), scale=p.get("rate", 1/p.get("rate", 1)) if "rate" in p else p.get("scale", 1), loc=p.get("loc", 0))
    if name == "logis":
        return d(loc=p.get("location", p.get("loc", 0)), scale=p.get("scale", 1))
    if name == "chisq":
        return d(df=p.get("df", p.get("shape", 1)), loc=p.get("loc", 0), scale=p.get("scale", 1))
    return d(**p)


def _call(distr: Any, kind: str, x: Any, para: Any):
    if callable(distr) and not isinstance(distr, str):
        return np.asarray(distr(kind, x, para), dtype=float)
    rv = _rv(distr, para)
    return np.asarray(getattr(rv, kind)(x), dtype=float)


def _opt(data, distr, start, objective, fix_arg=None, lower=None, upper=None, method="default", **kwargs):
    x = np.asarray(data, dtype=float)
    p0 = np.asarray(list(_asdict(start).values()) if isinstance(start, Mapping) else start, float)
    if p0.ndim == 0: p0 = p0[None]
    meth = "Nelder-Mead" if method == "default" and len(p0) > 1 else ("BFGS" if method == "default" else method)
    bounds = None
    if lower is not None or upper is not None:
        lo = np.full(len(p0), -np.inf) if lower is None else np.broadcast_to(lower, len(p0))
        hi = np.full(len(p0), np.inf) if upper is None else np.broadcast_to(upper, len(p0))
        bounds = list(zip(lo, hi))
        if meth == "BFGS": meth = "L-BFGS-B"
    def f(p):
        try:
            v = float(objective(p))
            return v if np.isfinite(v) else np.finfo(float).max
        except Exception:
            return np.finfo(float).max
    kw = {"method": meth}
    if bounds is not None: kw["bounds"] = bounds
    kw.update(kwargs)
    out = optimize.minimize(f, p0, **kw)
    return {"estimate": out.x, "convergence": int(not out.success), "value": float(out.fun),
            "optim.method": meth, "counts": getattr(out, "nfev", None),
            "loglik": float(-out.fun)}


def mledist(data, distr, start=None, fix_arg=None, optim_method="default",
            lower=None, upper=None, weights=None, **kwargs):
    x = np.asarray(data, float)
    w = np.ones(x.size) if weights is None else np.asarray(weights, float)
    def obj(p):
        z = _call(distr, "logpdf", x, p)
        return -float(np.sum(w*z) / x.size)
    if start is None:
        start = [np.mean(x), np.std(x, ddof=1)]
    r = _opt(x, distr, start, obj, fix_arg, lower, upper, optim_method, **kwargs)
    r["loglik"] = float(-np.sum(w * _call(distr, "logpdf", x, r["estimate"])))
    r["fix.arg"] = fix_arg
    return r


def qmedist(data, distr, probs, start=None, fix_arg=None, qtype=7,
            optim_method="default", lower=None, upper=None, weights=None, **kwargs):
    x = np.asarray(data, float)
    ps = np.asarray(probs, float)
    emp = np.quantile(x, ps, method="linear" if qtype == 7 else "linear")
    if weights is not None:
        order = np.argsort(x); xx, ww = x[order], np.asarray(weights)[order]
        emp = np.interp(ps, np.cumsum(ww)/np.sum(ww), xx)
    def obj(p):
        return float(np.mean((_call(distr, "ppf", ps, p) - emp)**2))
    if start is None: start = [np.mean(x), np.std(x, ddof=1)]
    r = _opt(x, distr, start, obj, fix_arg, lower, upper, optim_method, **kwargs)
    r.update({"probs": probs, "loglik": float(np.sum(_call(distr, "logpdf", x, r["estimate"])))})
    return r


def mmedist(data, distr, order, memp: Callable, start=None, fix_arg=None,
            optim_method="default", lower=None, upper=None, weights=None, **kwargs):
    x = np.asarray(data, float); orders = np.asarray(order, int)
    empirical = np.asarray([memp(x, int(o), weights) if weights is not None else memp(x, int(o)) for o in orders])
    def obj(p):
        rv = _rv(distr, p)
        theoretical = np.asarray([rv.moment(int(o)) for o in orders])
        return float(np.sum((empirical-theoretical)**2))
    if start is None: start = [np.mean(x), np.std(x, ddof=1)]
    r = _opt(x, distr, start, obj, fix_arg, lower, upper, optim_method, **kwargs)
    r.update({"order": order, "loglik": float(np.sum(_call(distr, "logpdf", x, r["estimate"])))})
    return r


def msedist(data, distr, start=None, fix_arg=None, phidiv="KL",
            optim_method="default", lower=None, upper=None, **kwargs):
    x = np.asarray(data, float)
    # Minimum spacing is most useful for continuous distributions.
    def obj(p):
        u = np.sort(np.clip(_call(distr, "cdf", x, p), 1e-15, 1-1e-15))
        spacings = np.diff(np.r_[0., u, 1.])
        return -float(np.mean(np.log(spacings)))
    if start is None: start = [np.mean(x), np.std(x, ddof=1)]
    r = _opt(x, distr, start, obj, fix_arg, lower, upper, optim_method, **kwargs)
    r["loglik"] = float(np.sum(_call(distr, "logpdf", x, r["estimate"])))
    return r


def mgedist(data, distr, gof="CvM", start=None, fix_arg=None,
            optim_method="default", lower=None, upper=None, **kwargs):
    x = np.sort(np.asarray(data, float)); n = x.size
    def obj(p):
        u = np.clip(_call(distr, "cdf", x, p), 1e-15, 1-1e-15)
        i = np.arange(1, n+1)
        if gof == "KS": return float(np.max(np.maximum(np.abs(u-i/n), np.abs(u-(i-1)/n))))
        if gof == "CvM": return float(1/(12*n*n) + np.mean((u-(2*i-1)/(2*n))**2))
        if gof == "AD": return float(-np.mean((2*i-1)*np.log(u*(1-u)))/n)
        return float(np.mean((u-(2*i-1)/(2*n))**2))
    if start is None: start = [np.mean(x), np.std(x, ddof=1)]
    r = _opt(x, distr, start, obj, fix_arg, lower, upper, optim_method, **kwargs)
    r.update({"gof": gof, "loglik": float(np.sum(_call(distr, "logpdf", x, r["estimate"])))})
    return r


def _grid(data, distr, plot_arg, min_arg, max_arg, lseq=50, fix_arg=None, loglik=True, weights=None):
    xs = np.linspace(min_arg[0], max_arg[0], int(lseq))
    ys = np.linspace(min_arg[1], max_arg[1], int(lseq))
    w = np.ones(len(data)) if weights is None else np.asarray(weights)
    z = np.empty((len(xs), len(ys)))
    for i, a in enumerate(xs):
        for j, b in enumerate(ys):
            p = {plot_arg[0]: a, plot_arg[1]: b}; p.update(_asdict(fix_arg))
            z[i, j] = np.sum(w * _call(distr, "logpdf" if loglik else "pdf", data, p))
    return {"x": xs, "y": ys, "z": z, "plot.arg": list(plot_arg)}


def llsurface(data, distr, plot_arg, min_arg, max_arg, lseq=50, fix_arg=None, loglik=True, **kwargs):
    return _grid(data, distr, plot_arg, min_arg, max_arg, lseq, fix_arg, loglik, kwargs.get("weights"))


def llcurve(data, distr, plot_arg, min_arg, max_arg, lseq=50, fix_arg=None, loglik=True, **kwargs):
    xs = np.linspace(min_arg[0], max_arg[0], int(lseq)); w = kwargs.get("weights")
    w = np.ones(len(data)) if w is None else np.asarray(w)
    y = []
    for a in xs:
        p = {plot_arg[0]: a}; p.update(_asdict(fix_arg))
        y.append(np.sum(w * _call(distr, "logpdf" if loglik else "pdf", data, p)))
    return {"x": xs, "y": np.asarray(y), "plot.arg": plot_arg}


def llplot(mlefit, loglik=True, expansion=1, lseq=50, **kwargs):
    est = np.asarray(mlefit["estimate"] if isinstance(mlefit, Mapping) else mlefit.estimate)
    sd = np.asarray(mlefit.get("sd", np.ones_like(est)) if isinstance(mlefit, Mapping) else mlefit.sd)
    names = mlefit.get("distname", "norm") if isinstance(mlefit, Mapping) else mlefit.distname
    data = mlefit["data"] if isinstance(mlefit, Mapping) else mlefit.data
    low, high = est-2*sd*expansion, est+2*sd*expansion
    if len(est) == 1: return llcurve(data, names, [list(_asdict(est).keys())[0]], low, high, lseq, mlefit.get("fix.arg") if isinstance(mlefit, Mapping) else None, loglik)
    keys = list(_asdict(est).keys())
    return llsurface(data, names, keys[:2], low[:2], high[:2], lseq, None, loglik)


def plotdist(data, distr, para, **kwargs):
    x = np.sort(np.asarray(data, float)); return {"x": x, "density": _call(distr, "pdf", x, para), "cdf": _call(distr, "cdf", x, para)}


def plotdistcens(censdata, distr, para, **kwargs):
    left = np.asarray(censdata["left"]); right = np.asarray(censdata["right"])
    return {"left": left, "right": right, "cdf.left": _call(distr, "cdf", left, para), "cdf.right": _call(distr, "cdf", right, para)}


def qqcomp(ft, **kwargs):
    fits = ft if isinstance(ft, (list, tuple)) else [ft]; data = np.sort(np.asarray(fits[0]["data"]))
    p = (np.arange(1, len(data)+1)-.5)/len(data)
    return {"observed": data, "theoretical": np.column_stack([_call(f["distname"], "ppf", p, f["estimate"]) for f in fits])}


def ppcomp(ft, **kwargs):
    fits = ft if isinstance(ft, (list, tuple)) else [ft]; data = np.sort(np.asarray(fits[0]["data"]))
    p = (np.arange(1, len(data)+1)-.5)/len(data)
    return {"empirical": p, "theoretical": np.column_stack([_call(f["distname"], "cdf", data, f["estimate"]) for f in fits])}


def ppcompcens(ft, **kwargs):
    return ppcomp(ft, **kwargs)


def prefit(data, distr, method="mle", feasible_par=None, **kwargs):
    if feasible_par is None: raise ValueError("feasible_par is required")
    if method == "mle": r = mledist(data, distr, start=feasible_par, **kwargs)
    elif method == "qme": r = qmedist(data, distr, start=feasible_par, probs=kwargs.pop("probs"), **kwargs)
    elif method == "mme": r = mmedist(data, distr, start=feasible_par, order=kwargs.pop("order"), memp=kwargs.pop("memp"), **kwargs)
    else: r = mgedist(data, distr, start=feasible_par, gof=kwargs.pop("gof", "CvM"), **kwargs)
    return dict(zip(_asdict(feasible_par).keys(), r["estimate"]))


__all__ = [n for n in globals() if not n.startswith("_")]
