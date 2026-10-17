"""Matplotlib ports of locfit's small plotting helpers.

The functions return the same useful data that the R helpers return.  Drawing
functions accept an optional Matplotlib ``Axes`` through ``ax`` and return
that axes; this keeps them composable while preserving R's invisible drawing.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

try:
    from ..locfit_raw import locfit_raw
except ImportError:  # loaded by the package proof loader
    from locfit_raw import locfit_raw
from .criteria import aic, cp, gcv
from .lcv import lcv


def _alphas(alpha):
    a = np.asarray(alpha, dtype=float)
    return a.reshape(1, -1) if a.ndim == 1 else a


def _fit(kwargs, alpha):
    kw = dict(kwargs)
    kw["alpha"] = alpha[0] if len(alpha) == 1 else alpha
    x, y = kw.pop("x"), kw.pop("y")
    return locfit_raw(x, y, **kw)


def _criterion_plot(kind, alpha, sig2=None, **kwargs):
    aa = _alphas(alpha)
    vals = []
    for row in aa:
        fit = _fit(kwargs, row)
        if kind == "aic":
            z = aic(fit)
            df, value = z["infl"], z["aic"]
        elif kind == "cp":
            z = cp(fit, sig2=1 if sig2 is None else sig2)
            df, value = z["vari"], z["cp"]
        elif kind == "gcv":
            z = gcv(fit)
            df, value = z["infl"], z["gcv"]
        elif kind == "lcv":
            lk = {k: v for k, v in kwargs.items() if k not in ("x", "y")}
            lk["alpha"] = row[0] if len(row) == 1 else row
            z = lcv(kwargs["x"], kwargs["y"], **lk)
            df, value = z["infl"], z["cv"]
        elif kind == "lscv":
            raise NotImplementedError("lscvplot requires the untranslated lscv routine")
        else:
            raise ValueError(kind)
        vals.append((df, value))
    df, values = np.asarray(vals, dtype=float).T
    return {"alpha": aa, "cri": kind.upper(), "df": df, "values": values}


def aicplot(alpha, **kwargs):
    return _criterion_plot("aic", alpha, **kwargs)


def cpplot(alpha, sig2=None, **kwargs):
    return _criterion_plot("cp", alpha, sig2=sig2, **kwargs)


def gcvplot(alpha, **kwargs):
    return _criterion_plot("gcv", alpha, **kwargs)


def lcvplot(alpha, **kwargs):
    return _criterion_plot("lcv", alpha, **kwargs)


def lscvplot(alpha, **kwargs):
    return _criterion_plot("lscv", alpha, **kwargs)


def plot_gcvplot(x, ax=None, xlab="Fitted DF", ylab=None, **kwargs):
    """Draw an object returned by any ``*plot`` criterion helper."""
    ax = plt.gca() if ax is None else ax
    ax.plot(np.asarray(x["df"]), np.asarray(x["values"]), **kwargs)
    ax.set(xlabel=xlab, ylabel=ylab or x.get("cri", ""))
    return ax


def plot_eval(x, add=False, text=False, ax=None, **kwargs):
    """Draw the evaluation cells/points of a two-dimensional fit."""
    ax = plt.gca() if ax is None else ax
    eva = x.get("eva", x)
    mi = x.get("mi", {})
    d = int(mi.get("d", 2))
    v = np.asarray(eva["xev"], dtype=float).reshape(-1, d)
    if not add:
        names = x.get("vnames", ["x", "y"])
        ax.set(xlabel=names[0], ylabel=names[1])
    if text:
        for i, (xx, yy) in enumerate(v[:, :2]):
            ax.text(xx, yy, str(i))
    else:
        ax.scatter(v[:, 0], v[:, 1], **kwargs)
    return ax


def plotbyfactor(x, y, f, col=None, pch="o", add=False, lg=None, ax=None,
                 xlab=None, ylab=None, **kwargs):
    """Plot numeric observations grouped by factor levels."""
    ax = plt.gca() if ax is None else ax
    xx, yy, ff = np.asarray(x), np.asarray(y), np.asarray(f)
    levels = list(dict.fromkeys(ff.tolist()))
    colors = list(range(1, 11)) if col is None else list(np.atleast_1d(col))
    markers = list(np.atleast_1d(pch))
    if not add:
        ax.set(xlabel=xlab or "x", ylabel=ylab or "y")
    for i, level in enumerate(levels):
        mask = ff == level
        ax.scatter(xx[mask], yy[mask], color=colors[i % len(colors)],
                   marker=markers[i % len(markers)], **kwargs)
    if lg is not None:
        ax.legend(levels, loc=lg)
    return ax


def panel_xyplot_lf(x, y, subscripts=None, clo=None, cup=None, wh=None,
                    ax=None, type="l", **kwargs):
    """Matplotlib panel equivalent for fitted/data observations and bands."""
    ax = plt.gca() if ax is None else ax
    n = len(x)
    ss = np.arange(n) if subscripts is None else np.asarray(subscripts)
    w = np.asarray(wh if wh is not None else np.repeat("f", n))[ss]
    xx, yy = np.asarray(x)[ss], np.asarray(y)[ss]
    fitted = w == "f"
    ax.plot(xx[fitted], yy[fitted], **kwargs)
    if clo is not None and cup is not None:
        ax.plot(xx[fitted], np.asarray(clo)[ss][fitted], "--", color="0.5")
        ax.plot(xx[fitted], np.asarray(cup)[ss][fitted], "--", color="0.5")
    data = w == "d"
    if np.any(data):
        ax.scatter(xx[data], yy[data])
    return ax


def panel_locfit(x, y, z=None, ax=None, contour=False, **kwargs):
    """Matplotlib panel equivalent; contour mode draws a fitted 2-D surface."""
    ax = plt.gca() if ax is None else ax
    if z is None:
        ax.scatter(x, y, **kwargs)
        return ax
    x, y, z = np.asarray(x), np.asarray(y), np.asarray(z)
    if contour:
        ax.tricontourf(x, y, z)
    else:
        ax.scatter(x, y, c=z, **kwargs)
    return ax


__all__ = ["aicplot", "cpplot", "gcvplot", "lcvplot", "lscvplot",
           "plot_gcvplot", "plot_eval", "plotbyfactor", "panel_locfit",
           "panel_xyplot_lf"]
