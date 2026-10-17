"""density.lf: one-dimensional local-likelihood density estimate (R locfit 1.5-9.12).

R's ``density.lf`` runs ``locfit.raw(lp(x, h = h, deg = deg), ev = ev,
kern = kern, link = "ident", family = "density")`` with the default
``ev = lfgrid(mg = n, ll = from, ur = to)``. The density family is in
``crates/locfit`` (``density_lf.rs``): for one dimension, degree 0, and the
identity link, the fitted density is a kernel sum divided by ``n * h * int W``.

The supported arguments are the R defaults for ``ev``, ``family``, and
``link``, and degree 0. The window names ``gaussian``, ``rectangular``, and
``triangular`` map to the kernels ``gauss``, ``rect``, and ``tria``, as in R.
A kernel name is passed through as R does. Anything else raises
``NotImplementedError``: degree 1 and higher (the local linear and quadratic
density, which needs the full Newton system), a user ``ev``, ``renorm``, the
``cosine`` window (R has no kernel for it), and user limits.

The return value is a dict with ``x`` (the grid) and ``y`` (the density at
each grid point), as R's ``list(x = ..., y = ...)``.
"""

from __future__ import annotations

import math

import numpy as np

import locfit as _crate

_WINDOWS = {"rectangular": "rect", "triangular": "tria", "gaussian": "gauss"}


def density_lf(x, n=50, window="gaussian", width=None, from_=None, to=None,
               cut=None, ev=None, deg=0, **kwargs):
    if ev is not None:
        raise NotImplementedError("density.lf: only the default ev = lfgrid() is ported")
    if deg != 0:
        raise NotImplementedError("density.lf: only deg = 0 is ported")
    for key, val in kwargs.items():
        if key == "family" and val == "density":
            continue
        if key == "link" and val == "ident":
            continue
        raise NotImplementedError(f"density.lf: argument {key!r} is not ported")
    if window == "cosine":
        raise NotImplementedError("density.lf: the cosine window has no kernel in R locfit")

    xs = np.sort(np.asarray(x, dtype=float).reshape(-1))
    if xs.size == 0:
        raise ValueError("density.lf needs at least one observation")
    r0, r1 = float(xs[0]), float(xs[-1])
    kern = _WINDOWS.get(window, window)
    gauss = kern == "gauss"
    # R: cut = 0.75 for the Gaussian window, 0.5 otherwise.
    cut_v = (0.75 if gauss else 0.5) if cut is None else float(cut)
    if width is None:
        nbar = math.log(xs.size, 2.0) + 1.0
        width = (r1 - r0) / nbar * 0.5
    width = float(width)
    fl = r0 - width * cut_v if from_ is None else float(from_)
    fr = r1 + width * cut_v if to is None else float(to)
    if fr <= fl:
        raise ValueError("Invalid from/to values")
    h = width / 2.0
    if gauss:
        h *= 1.25

    mg = int(n)
    # gridf: x_i = ((mg - 1 - i) * ll + i * ur) / (mg - 1).
    idx = np.arange(mg, dtype=float)
    grid = ((mg - 1 - idx) * fl + idx * fr) / (mg - 1)
    # The crate takes the long kernel names (kernel_from_str).
    crate_kern = {"gauss": "gaussian", "rect": "rectangular", "tria": "triangular"}.get(kern, kern)
    y = np.asarray(_crate.density_lf_grid(xs, grid, h, crate_kern), dtype=float)
    return {"x": grid, "y": y}


__all__ = ["density_lf"]
