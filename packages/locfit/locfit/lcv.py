"""Leave-one-out local-fit criterion for numeric data.

R's ``lcv(x, ...)`` returns ``lik``, ``infl``, ``vari`` and ``cv``: the
``lk``, ``df1`` and ``df2`` of the fit's ``dp``, and the sum of the
cross-validated squared residuals (``residuals(fit, type = "d2", cv = TRUE)``).

Default path (R's ``ev = rbox()``, the adaptive kd-tree): the crate computes the
leave-one-out sum on the tree (``cv_sum`` of ``locfit_fit``). It follows locfit's
``fitted.c`` ``cv`` branch: ``th_cv = th - t0^2 * w * (y - th)`` with ``t0`` the
tree-interpolated influence factor at each data point, and the sum of
``w * (y - th_cv)^2``.

``ev = {"type": "data"}`` (R's ``ev = dat()``) keeps the probing form: the fit is
linear in ``y`` at a fixed bandwidth, so the hat diagonal ``H_ii`` is the fit at
point ``i`` for the unit vector ``e_i``, and ``th_cv = th - H_ii * (y - th)``.
"""

from __future__ import annotations

import numpy as np

try:
    from ..locfit_raw import locfit_raw
except ImportError:  # loaded by file path, with packages/locfit on sys.path
    from locfit_raw import locfit_raw


def lcv(x, y=None, **kwargs):
    if y is None and isinstance(x, dict):
        y = x["y"]
        x = x["x"]
    if y is None:
        raise ValueError("numeric use requires x and y")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    y = np.asarray(y, dtype=float).reshape(-1)
    ev = kwargs.pop("ev", None)
    if ev is None or (isinstance(ev, dict) and ev.get("type") == "tree"):
        # R's default ev = rbox(): the tree fit and its leave-one-out sum.
        cut = float(ev.get("cut", 0.8)) if isinstance(ev, dict) else 0.8
        fit = locfit_raw(x, y, ev=None if ev is None else {"type": "tree", "cut": cut},
                         **kwargs)
        dp = fit["dp"]
        return {"lik": float(dp["lk"]), "infl": float(dp["df1"]),
                "vari": float(dp["df2"]), "cv": float(fit["cv"])}
    if not (isinstance(ev, dict) and ev.get("type") == "data"):
        raise NotImplementedError(
            f"lcv: ev type {ev.get('type') if isinstance(ev, dict) else ev!r} is not translated.")
    fit = locfit_raw(x, y, ev=ev, **kwargs)
    dp = fit["dp"]
    th = np.asarray(fit["fitted"], dtype=float)
    res = y - th
    n = len(y)
    hii = np.empty(n)
    for i in range(n):
        e = np.zeros(n)
        e[i] = 1.0
        probe = locfit_raw(x, e, ev=ev, **kwargs)
        hii[i] = np.asarray(probe["fitted"], dtype=float)[i]
    cv_th = th - hii * res
    return {"lik": float(dp["lk"]), "infl": float(dp["df1"]),
            "vari": float(dp["df2"]), "cv": float(np.sum((y - cv_th) ** 2))}


__all__ = ["lcv"]
