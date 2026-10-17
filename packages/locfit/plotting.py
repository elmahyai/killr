"""Matplotlib ports of locfit plotting helpers."""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .locfit_raw import locfit_raw
try:
    from .lcv import lcv
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).with_name("locfit")))
    from lcv import lcv

def _dp(fit):
    d = fit.get("dp", fit)
    return float(d.get("lk", 0)), float(d.get("df1", 0)), float(d.get("df2", 0))

def _alphas(alpha):
    a = np.asarray(alpha, dtype=float)
    return a.reshape(1, -1) if a.ndim == 1 else a

def _fit(kwargs, row):
    kw = dict(kwargs)
    kw["alpha"] = row[0] if len(row) == 1 else row
    return locfit_raw(kw.pop("x"), kw.pop("y"), **kw)

def _criterion_plot(kind, alpha, sig2=None, **kwargs):
    rows, vals = _alphas(alpha), []
    for row in rows:
        if kind == "lcv":
            kw = {k: v for k, v in kwargs.items() if k not in ("x", "y")}
            kw["alpha"] = row[0] if len(row) == 1 else row
            z = lcv(kwargs["x"], kwargs["y"], **kw)
            vals.append((z["infl"], z["cv"]))
        elif kind == "lscv":
            from .lscv import lscv
            z = lscv(kwargs["x"], kwargs["y"], alpha=row[0] if len(row) == 1 else row)
            if isinstance(z, dict):
                vals.append((z["infl"], z["lscv"]))
            else:
                z = np.asarray(z, dtype=float).reshape(-1)
                vals.append((z[1], z[0]))
        else:
            lk, df1, df2 = _dp(_fit(kwargs, row))
            if kind == "aic":
                z = {"infl": df1, "aic": -2 * lk + 2 * df1}
            elif kind == "gcv":
                n = float(_fit(kwargs, row).get("mi", {}).get("n", len(kwargs["y"])))
                z = {"infl": df1, "gcv": -2 * n * lk / (n - df1) ** 2}
            else:
                fit = _fit(kwargs, row)
                n = float(fit.get("mi", {}).get("n", len(kwargs["y"])))
                s2 = 1 if sig2 is None else sig2
                z = {"vari": df2, "cp": (-2 * lk) / s2 - n + 2 * df1}
            vals.append((z["infl"] if kind != "cp" else z["vari"], z[kind]))
    df, values = np.asarray(vals, dtype=float).T
    return {"alpha": rows, "cri": kind.upper(), "df": df, "values": values}

def aicplot(alpha, **kwargs): return _criterion_plot("aic", alpha, **kwargs)
def cpplot(alpha, sig2=None, **kwargs): return _criterion_plot("cp", alpha, sig2, **kwargs)
def gcvplot(alpha, **kwargs): return _criterion_plot("gcv", alpha, **kwargs)
def lcvplot(alpha, **kwargs): return _criterion_plot("lcv", alpha, **kwargs)
def lscvplot(alpha, **kwargs): return _criterion_plot("lscv", alpha, **kwargs)

def plot_gcvplot(x, ax=None, xlab="Fitted DF", ylab=None, **kwargs):
    ax = plt.gca() if ax is None else ax
    ax.plot(x["df"], x["values"], **kwargs)
    ax.set(xlabel=xlab, ylabel=ylab or x["cri"])
    return ax

def plot_eval(x, add=False, text=False, ax=None, **kwargs):
    ax = plt.gca() if ax is None else ax
    eva, d = x.get("eva", x), int(x.get("mi", {}).get("d", 2))
    v = np.asarray(eva["xev"], dtype=float).reshape(-1, d)
    if text:
        for i, (xx, yy) in enumerate(v[:, :2]): ax.text(xx, yy, str(i))
    else: ax.scatter(v[:, 0], v[:, 1], **kwargs)
    return ax

def plotbyfactor(x, y, f, col=None, pch="o", add=False, lg=None, ax=None, **kwargs):
    ax = plt.gca() if ax is None else ax
    xx, yy, ff = np.asarray(x), np.asarray(y), np.asarray(f)
    levels = list(dict.fromkeys(ff.tolist()))
    colors, markers = list(np.atleast_1d(col if col is not None else "C0")), list(np.atleast_1d(pch))
    for i, lev in enumerate(levels):
        m = ff == lev
        ax.scatter(xx[m], yy[m], color=colors[i % len(colors)], marker=markers[i % len(markers)], **kwargs)
    if lg is not None: ax.legend(levels, loc=lg)
    return ax

def panel_xyplot_lf(x, y, subscripts=None, clo=None, cup=None, wh=None, ax=None, **kwargs):
    ax = plt.gca() if ax is None else ax
    ss = np.arange(len(x)) if subscripts is None else np.asarray(subscripts)
    w = np.asarray(wh if wh is not None else np.repeat("f", len(x)))[ss]
    xx, yy = np.asarray(x)[ss], np.asarray(y)[ss]
    ax.plot(xx[w == "f"], yy[w == "f"], **kwargs)
    if clo is not None and cup is not None:
        ax.plot(xx[w == "f"], np.asarray(clo)[ss][w == "f"], "--", color="0.5")
        ax.plot(xx[w == "f"], np.asarray(cup)[ss][w == "f"], "--", color="0.5")
    if np.any(w == "d"): ax.scatter(xx[w == "d"], yy[w == "d"])
    return ax

def panel_locfit(x, y, z=None, ax=None, contour=False, **kwargs):
    ax = plt.gca() if ax is None else ax
    if z is None: ax.scatter(x, y, **kwargs)
    elif contour: ax.tricontourf(x, y, z)
    else: ax.scatter(x, y, c=z, **kwargs)
    return ax

__all__ = ["aicplot", "cpplot", "gcvplot", "lcvplot", "lscvplot", "plot_gcvplot",
           "plot_eval", "plotbyfactor", "panel_locfit", "panel_xyplot_lf"]
