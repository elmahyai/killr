"""Local polynomial hat matrix for a numeric ``x, y`` fit.

R's ``hatmatrix()`` returns the operator H with ``H %*% y`` equal to the fitted
values. Here H is the direct local fit at the data (``ev = dat()``), which is
the reference the proof uses (R's ``t(locfit.raw(..., geth = 1, ev = dat()))``).
R's ``hatmatrix()`` itself stops on that data with "data is too long" because it
uses the default ``ev = rbox()`` tree, and that tree is not in crates/locfit.

At a fixed bandwidth the local fit is linear in ``y``. The bandwidth comes from
``x`` alone (``alpha``, the nearest-neighbour fraction), so column ``i`` of H is
the fit to the unit vector ``e_i``. Each column comes from the crate's fit.
"""

from __future__ import annotations

import numpy as np

from locfit_raw import locfit_raw


def hatmatrix(formula=None, dc=True, **kwargs):
    if isinstance(formula, dict):
        x, y = formula["x"], formula["y"]
    else:
        x, y = kwargs.pop("x", formula), kwargs.pop("y", None)
    if y is None:
        raise ValueError("numeric use requires x and y")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    n = len(np.asarray(y).reshape(-1))
    alpha = kwargs.pop("alpha", 0.7)
    deg = kwargs.pop("deg", 2)
    kern = kwargs.pop("kern", "tricube")
    kt = kwargs.pop("kt", "sph")
    if kwargs:
        raise TypeError("hatmatrix: arguments not in crates/locfit: "
                        + ", ".join(sorted(kwargs)))
    hmat = np.empty((n, n))
    for i in range(n):
        e = np.zeros(n)
        e[i] = 1.0
        fit = locfit_raw(x, e, alpha=alpha, deg=deg, kern=kern, kt=kt,
                         ev={"type": "data"})
        hmat[:, i] = np.asarray(fit["fitted"], dtype=float)
    return hmat


__all__ = ["hatmatrix"]
