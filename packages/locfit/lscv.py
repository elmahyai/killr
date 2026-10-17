"""lscv: R's least-squares cross-validation bandwidth for a density sample.

``exact = TRUE`` goes to lscv_exact (slscv, the exact criterion). The default
calls locfit.raw with geth = 6, the density LSCV path: the density family with
the log link, fitted at the default ``ev = rbox()`` (the adaptive tree, with
its vertices interpolated at the data), then the criterion and degrees of
freedom. ``lscv_tree`` in the crate is that path. ``ev = dat()`` (every
observation is a vertex) is ``dens_lscv`` in the crate.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ._kernel import dens_lscv, lscv_tree

#: R's rbox() default split threshold.
RBOX_CUT = 0.8


def lscv(x, *args, exact=False, **kwargs):
    if exact:
        from .lscv_exact import lscv_exact

        return lscv_exact(x, *args, **kwargs)
    xa = np.asarray(x, dtype=float)
    if xa.ndim == 2 and xa.shape[1] > 1:
        # R's density path integrates over the domain; for d >= 2 R's dens_integrate
        # warns and returns 0. crates/locfit has only the one-dimensional density.
        raise NotImplementedError("lscv for d >= 2 (two-dimensional density) is not in crates/locfit")
    ev = kwargs.pop("ev", None)
    cut = RBOX_CUT
    if ev is not None and not (isinstance(ev, Mapping) and ev.get("type") in ("tree", "data")):
        raise NotImplementedError("lscv for ev other than rbox() or dat() is not in crates/locfit")
    alpha = kwargs.pop("alpha", 0.7)
    al = np.concatenate([np.atleast_1d(np.asarray(alpha, dtype=float)), np.zeros(3)])[:3]
    if al[2] != 0.0:
        raise NotImplementedError("adpen (adaptive penalty) is not in crates/locfit")
    deg = int(np.atleast_1d(np.asarray(kwargs.pop("deg", 2))).reshape(-1)[0])
    kern = kwargs.pop("kern", "tricube")
    if kwargs:
        raise TypeError("lscv: arguments not in crates/locfit: " + ", ".join(sorted(kwargs)))
    if ev is None or ev.get("type") == "tree":
        if ev is not None:
            cut = float(ev.get("cut", RBOX_CUT))
        return lscv_tree(x, al[0], al[1], deg, kern, cut)
    return dens_lscv(x, al[0], al[1], deg, kern)
