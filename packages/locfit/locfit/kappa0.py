"""Critical value for a normal local-fit confidence band from the grid fit.

R's ``kappa0(formula, cov, ev = lfgrid(20))`` fits with ``geth = 2`` and
``dc = TRUE`` on the grid, takes the tube constants ``const`` and the
dimension ``d`` of that fit, and returns ``crit(const = z$const, d = z$d,
cov = cov)``.

The tube constants are the ``geth = 2`` output of locfit's ``constants``
(``scb_cons.c`` ``tube_constants`` on the ``ISIMPSON`` grid, with the weight
diagrams of ``wdiag``). They come from ``crates/locfit`` (``kappa0.rs``,
``kappa0_const``). The critical value is ``crit()`` of this package, which
calls the crate's ``scritval`` for a general ``const``.

Ported for ``d = 1`` and ``d = 2``, the tricube kernel, degree 2 and the
spherical kernel type. Other settings raise instead of returning an
approximation.
"""

from __future__ import annotations

import numpy as np

try:
    from .crit import crit
except ImportError:  # loaded by file path, without a package
    import importlib.util as _ilu
    from pathlib import Path as _Path

    _spec = _ilu.spec_from_file_location(
        "locfit_kappa0_crit", _Path(__file__).with_name("crit.py"))
    _module = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    crit = _module.crit


def _grid_mg(ev):
    if ev is None:
        return 20
    if isinstance(ev, dict) and ev.get("type") == "grid":
        mg = np.asarray(ev.get("mg", 20)).reshape(-1)
        if mg.size == 0 or np.any(mg != mg[0]):
            raise NotImplementedError("kappa0: grid ev with unequal mg is not ported")
        ll = np.asarray(ev.get("ll", 0.0), dtype=float).reshape(-1)
        ur = np.asarray(ev.get("ur", 0.0), dtype=float).reshape(-1)
        if np.any(ll != 0.0) or np.any(ur != 0.0):
            raise NotImplementedError("kappa0: grid ev with ll or ur limits is not ported")
        return int(mg[0])
    raise NotImplementedError(
        f"kappa0: ev {ev!r} is not translated; use lfgrid(mg) or the default.")


def kappa0(formula=None, cov=0.95, ev=None, **kwargs):
    if isinstance(formula, dict):
        x, y = formula["x"], formula["y"]
    else:
        x, y = kwargs.pop("x", formula), kwargs.pop("y", None)
    if y is None:
        raise ValueError("numeric use requires x and y")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    alpha = kwargs.pop("alpha", 0.7)
    deg = kwargs.pop("deg", 2)
    kern = kwargs.pop("kern", "tricube")
    kt = kwargs.pop("kt", "sph")
    if kwargs:
        raise TypeError("kappa0: arguments not in crates/locfit: "
                        + ", ".join(sorted(kwargs)))
    if int(deg) != 2:
        raise NotImplementedError("kappa0: only degree 2 is ported")
    if kern != "tricube" or kt != "sph":
        raise NotImplementedError("kappa0: only the tricube kernel and kt = 'sph' are ported")
    mg = _grid_mg(ev)

    # Imported here so the translated package does not need the crate unless
    # kappa0 is called.
    import locfit as crate  # crates/locfit, the loaded C kernel

    const = crate.kappa0_const(x, nn=float(alpha), fixh=0.0, deg=2,
                               kern="tricube", kt="sph", mg=mg)
    d = x.shape[1]
    return crit(const=tuple(float(v) for v in const), d=d, cov=cov)


__all__ = ["kappa0"]
