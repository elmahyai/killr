"""gam.lf: GAM smoother residuals, variance factors, nonlinear df, and prediction
(R locfit 1.5-9.12).

R's ``gam.lf(x, y, w)`` calls ``locfit.raw(x, y, weights = w, geth = 4)`` and
returns ``residuals``, ``var``, and ``nl.df``. With ``xeval`` it calls
``locfit.raw(..., geth = 5)`` and then ``predict(fit, xeval)``. The default
evaluation is ``ev = rbox()``, the kd-tree vertex interpolation, which
``crates/locfit`` provides (``fit_tree``).

What is ported:

- ``nl.df``: ``dp["df1"] - 2`` in R. ``dp["df1"]`` is the trace of the
  influence factors at the data (``df0`` in the crate), so ``nl.df`` is
  ``df0 - 2``.
- ``residuals``: the local fit's residuals ``y - fitted``, then the residuals of
  a weighted least-squares fit of those on ``1, x_1, ..., x_d`` (locfit's
  orthogonal residuals, ``ressumm`` with ``GAMF``). Weights are ``w``.
- ``var``: R does not return a per-observation variance. ``geth = 4`` returns
  ``z$wdes[n * (p + 2) + p * p + (1:n)]``, a slice of the design work array
  ``wk`` that ``ressumm`` leaves behind (``locfit.c`` ``des_init`` layout:
  ``X``, ``w``, ``res``, ``di``, ``th``, ``wd``, ``V``, ...). The orthogonal
  step sets ``di[i] = min(1, nlx_i^2 * w_i)`` (``frend.c``), then overwrites
  ``th`` with the orthogonal fit and leaves ``wd = y - fitted`` in place. R
  reads ``p * p`` entries past the start of ``di``, so ``var[k]`` is the
  arena entry ``p * p + k`` of ``[di, th, wd]``. ``p`` is ``calcp(d, deg)``.
  The result can be negative, and the slice wraps from ``di`` into ``th`` and
  ``wd``; it is reproduced as R computes it. Only the arena up to ``wd`` is
  reproduced: beyond that R reads the orthogonal fit's internal ``V`` storage,
  which is not ported.
- ``xeval``: ``predict`` at new points, the kd-tree vertex interpolation of the
  coefficient plus the parametric component at each point (``preplot``,
  ``where = "vect"``), computed by ``crates/locfit`` (``xnew_fitted``).

``alpha`` (``nn``), ``deg`` and ``kern`` (R partial matching, as ``pmatch``) are
passed to the crate; the defaults are those of ``locfit.raw``. ``ev`` is
``"rbox"`` (``rbox()``, the kd-tree, default) or ``"dat"`` (``dat()``, the fit
at each data point, locfit ``EDATA``); other ``ev`` values are not ported.
"""

from __future__ import annotations

from math import comb

import numpy as np

import locfit as _crate


def _var_from_arena(n, p, di, th, wd):
    """R ``z$wdes[n*(p+2) + p*p + (1:n)]``, read from the design arena.

    The arena is ``[di (n), th (n), wd (n)]``, starting at ``n*(p+2)``. Entry
    ``p*p + k`` of the arena is R's value ``var[k]``.
    """
    arena = np.concatenate([np.asarray(di, float), np.asarray(th, float),
                            np.asarray(wd, float)])
    start = p * p
    if start + n > arena.size:
        raise NotImplementedError(
            "gam.lf: var reads past the wd block of the design arena (p^2 > 2n); "
            "not ported")
    return arena[start:start + n].copy()


# locfit kernel names (lfstr.c wfuns); R matches `kern` by unique prefix (pmatch).
_WFUNS = ["rectangular", "epanechnikov", "bisquare", "tricube", "triweight",
          "gaussian", "triangular", "ququ", "6cub", "minimax", "exponential",
          "maclean", "parametric"]
_KERN_PORTED = {"rectangular", "epanechnikov", "bisquare", "tricube", "triweight",
                "gaussian", "triangular", "ququ", "6cub", "exponential"}


def _kern_name(kern):
    if kern in _WFUNS:
        full = kern
    else:
        hits = [f for f in _WFUNS if f.startswith(kern)]
        if len(hits) != 1:
            raise NotImplementedError(f"gam.lf: kern {kern!r} does not match one kernel")
        full = hits[0]
    if full not in _KERN_PORTED:
        raise NotImplementedError(f"gam.lf: kern {full!r} is not ported")
    return full


def gam_lf(x, y, w=None, xeval=None, alpha=0.7, deg=2, kern="tricube", ev="rbox", **kwargs):
    if kwargs:
        raise NotImplementedError(f"gam.lf: argument {next(iter(kwargs))!r} is not ported")
    kern_name = _kern_name(kern)
    if deg == 0:
        # R's residuals are all NaN for deg = 0 (not reproduced; see the proof notes).
        raise NotImplementedError("gam.lf: deg = 0 gives NaN residuals in R; not ported")
    if ev not in ("rbox", "dat"):
        raise NotImplementedError(f"gam.lf: ev {ev!r} is not ported")
    if ev == "dat" and xeval is not None:
        raise NotImplementedError("gam.lf: xeval with ev = dat() is not ported")
    tree = ev == "rbox"

    X = np.asarray(x, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    yv = np.asarray(y, dtype=float).reshape(-1)
    n, d = X.shape
    wv = np.ones(n) if w is None else np.asarray(w, dtype=float).reshape(-1)

    if xeval is not None:
        Xe = np.asarray(xeval, dtype=float)
        Xe = np.ascontiguousarray(Xe.reshape(-1, d))
        fit = _crate.locfit_fit(np.ascontiguousarray(X), np.ascontiguousarray(yv),
                                weights=np.ascontiguousarray(wv), xev=Xe,
                                nn=alpha, deg=deg, kern=kern_name, kt="spherical",
                                tree=tree, cut=0.8)
        return np.asarray(fit["xnew_fitted"], dtype=float)

    fit = _crate.locfit_fit(np.ascontiguousarray(X), np.ascontiguousarray(yv),
                            weights=np.ascontiguousarray(wv), nn=alpha, deg=deg,
                            kern=kern_name, kt="spherical", tree=tree, cut=0.8)
    fitted = np.asarray(fit["fitted"], dtype=float)

    # locfit ressumm (GAMF): residuals of a weighted linear fit to y - fitted.
    wd = yv - fitted
    A = np.column_stack([np.ones(n), X])
    sw = np.sqrt(wv)
    coef = np.linalg.lstsq(A * sw[:, None], wd * sw, rcond=None)[0]
    th_orth = A @ coef            # locfit overwrites th with this fit
    residuals = wd - th_orth

    # locfit ressumm (frend.c): di[i] = min(1, nlx_i^2 * w_i) for the orthogonal step.
    nlx = np.asarray(fit["nlx_data"], dtype=float)
    di = np.minimum(1.0, nlx * nlx * wv)

    p = comb(d + deg, deg)        # calcp(spherical, d, deg); R's mi["p"]
    var = _var_from_arena(n, p, di, th_orth, wd)

    nl_df = float(fit["df0"]) - 2.0
    return {"residuals": residuals, "var": var, "nl.df": nl_df}


__all__ = ["gam_lf"]
