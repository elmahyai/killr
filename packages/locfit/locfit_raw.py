"""locfit.raw: R's locfit.raw() on the crates/locfit kernel.

The kernel covers the Gaussian identity (quasi) family, spherical and product
kernels, degree 0 to 2, and fits at the data (``ev = list(type = "data")``),
at given points (numeric ``ev``), or on the default ``ev = rbox()`` adaptive
tree (the vertices are interpolated at the data). Not in the kernel, and raised here:

- censored data (``cens != 0``), binomial and other families,
- ``geth`` other than 0, ``scale = TRUE``, adaptive ``adpen``, ``acri``.

The result holds R's ``eva$coef`` layout in ``eva`` (coef | nlx | t0 | lik | h,
without R's trailing informational column), and the ``dp`` summaries.
R's fitted values at the data come from the kernel's ``sfitted`` output (``fitted``).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ._kernel import KERNEL_TG, raw_fit, rep
from .lp import LpMatrix

def locfit_raw(x, y=None, weights=1, cens=0, base=0, scale=False, alpha=0.7,
               deg=2, kern="tricube", kt="sph", acri="none", ev=None, geth=0,
               **kwargs):
    # Any other R argument (xlim, family, link, mint, maxit, deriv, ...) is not in the kernel.
    if kwargs:
        raise TypeError("locfit_raw: arguments not in crates/locfit: "
                        + ", ".join(sorted(kwargs)))
    if isinstance(x, LpMatrix):
        alpha, deg, scale, acri = x.alpha, x.deg, x.scale, x.acri
    if y is None:
        raise NotImplementedError("locfit.raw without y is the density family; "
                                  "not in crates/locfit")
    if np.asarray(y).dtype == bool:
        raise NotImplementedError("logical y is the binomial family; "
                                  "not in crates/locfit")
    xm = np.asarray(x, dtype=float)
    if xm.ndim == 1:
        xm = xm.reshape(-1, 1)
    n, d = xm.shape
    yv = np.asarray(y, dtype=float).reshape(-1)
    if yv.size != n:
        raise ValueError("x and y must have the same number of rows")

    w_vec = rep(weights, n)
    w_arg = None if np.isscalar(weights) and float(weights) == 1.0 else w_vec
    c_vec = rep(cens, n)
    if np.any(c_vec != 0):
        raise NotImplementedError("censored Gaussian data (cens != 0) is not in crates/locfit")
    b_vec = rep(base, n)
    b_arg = b_vec if np.any(b_vec != 0) else None

    if np.any(np.asarray(scale, dtype=bool)):
        raise NotImplementedError("scale = TRUE is not in crates/locfit")
    al = np.concatenate([np.atleast_1d(np.asarray(alpha, dtype=float)), np.zeros(3)])[:3]
    if al[2] != 0.0:
        raise NotImplementedError("adpen (adaptive penalty) is not in crates/locfit")
    dg = np.atleast_1d(np.asarray(deg)).astype(int)
    if dg.size == 2 and dg[0] == dg[1]:
        dg = dg[:1]
    if dg.size != 1:
        raise NotImplementedError("unequal deg pair is not in crates/locfit")
    deg_i = int(dg[0])
    if acri != "none":
        raise NotImplementedError("acri (adaptive criterion) is not in crates/locfit")
    if geth:
        raise NotImplementedError("geth != 0 (other fit outputs) is not in crates/locfit")

    tree = False
    cut = 0.8
    if ev is None or (isinstance(ev, Mapping) and ev.get("type") == "tree"):
        # R's default ev = rbox(): the adaptive tree, fitted at its vertices.
        tree = True
        xev = None
        if ev is not None:
            cut = float(ev.get("cut", 0.8))
    elif isinstance(ev, Mapping):
        if ev.get("type") != "data":
            raise NotImplementedError(f"ev type {ev.get('type')!r} is not in crates/locfit")
        xev = None
    else:
        e = np.asarray(ev, dtype=float)
        if e.ndim == 2:
            if e.shape[1] != d:
                raise ValueError("evaluation points have the wrong dimension")
            xev = e
        else:
            if e.size % d:
                raise ValueError("ev length is not a multiple of d")
            # R stores the points column by column (as.vector of an mg x d matrix).
            xev = e.reshape(d, e.size // d).T
        xev = np.ascontiguousarray(xev)

    out = raw_fit(
        np.ascontiguousarray(xm), np.ascontiguousarray(yv),
        weights=None if w_arg is None else np.ascontiguousarray(w_arg),
        base=None if b_arg is None else np.ascontiguousarray(b_arg),
        xev=xev, nn=al[0], fixh=al[1], deg=deg_i, kern=kern, kt=kt,
        tree=tree, cut=cut,
    )
    coef = np.asarray(out["coef"], dtype=float)
    nlx = np.asarray(out["nlx"], dtype=float)
    t0 = np.asarray(out["t0"], dtype=float)
    lik = np.asarray(out["lik"], dtype=float)
    h = np.asarray(out["h"], dtype=float)
    if tree:
        # The evaluation points are the tree vertices (R's eva$xev).
        xev_out = np.asarray(out["xev"], dtype=float)
        ev_name = "tree"
        nlx_data = np.asarray(out["nlx_data"], dtype=float)
    else:
        xev_out = xm if xev is None else xev
        ev_name = "data" if xev is None else "pres"
        nlx_data = None
    return {
        "eva": np.hstack([coef, nlx, t0, lik, h[:, None]]),
        "coef": coef, "nlx": nlx, "t0": t0, "lik": lik, "h": h,
        "xev": xev_out,
        "dp": {"lk": float(out["lk"]), "df1": float(out["df0"]),
               "df2": float(out["df1"]), "rv": float(out["rv"]),
               "rsc": float(out["rsc"])},
        "mi": {"n": n, "d": d, "deg": deg_i, "tg": KERNEL_TG},
        "alpha": al, "kern": kern, "kt": kt,
        "fitted": None if (xev is not None and not tree) else np.asarray(out["fitted"], dtype=float),
        "nlx_data": nlx_data,
        # R's sum(residuals(fit, type = "d2", cv = TRUE)) on the tree; used by lcv.
        "cv": float(out["cv_sum"]) if tree else None,
        "ev": ev_name,
        "data": {
            "x": xm, "y": yv,
            "weights": 1.0 if w_arg is None else w_vec,
            "cens": 0.0 if not np.any(c_vec) else c_vec,
            "base": 0.0 if b_arg is None else b_vec,
        },
        "call": "locfit.raw",
    }


def fitted(fit):
    """R's fitted.locfit (what = "coef", type = "fit") at the data.

    The values come from the crate's ``sfitted`` output, stored on the fit by
    ``locfit_raw``. A fit at given points has no data fitted values here.
    """
    vals = fit.get("fitted") if isinstance(fit, Mapping) else None
    if vals is None:
        raise NotImplementedError(
            "fitted.locfit at given points (ev = numeric) is not in crates/locfit; "
            "use ev = {'type': 'data'}")
    return np.asarray(vals, dtype=float)


def residuals(fit):
    """R's residuals(type = 'raw'): y - fitted."""
    return fit["data"]["y"] - fitted(fit)


def se_fit(fit):
    """R's predict(fit, newdata = data, se.fit = TRUE), band = 'global', at the data.

    locfit's preplot takes the standard-error factor at each point (the
    interpolated PNLX, with the parametric part) and multiplies by
    sigmahat = sqrt(rv). Only the tree fit (default ev = rbox()) has it here.
    """
    nlx = fit.get("nlx_data") if isinstance(fit, Mapping) else None
    if nlx is None:
        raise NotImplementedError(
            "se.fit at the data is only in crates/locfit for the tree fit (default ev = rbox())")
    return np.sqrt(fit["dp"]["rv"]) * np.asarray(nlx, dtype=float)
