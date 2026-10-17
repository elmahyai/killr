"""Bridge from the translated locfit wrappers to the crates/locfit kernel.

The kernel is the compiled module ``locfit`` built from crates/locfit (maturin).
It gives R's ``eva$coef`` layout, the likelihood columns, the ``dp``
summaries and the data fitted values for the Gaussian identity (quasi) family,
at the data, at given points, or on the adaptive tree that R's default
``ev = rbox()`` builds (``tree=True``, the vertices are interpolated at the
data). It does not give the censored family or the Gaussian-kernel density.
Those raise NotImplementedError in the wrappers that need them. The kernel
also gives ``sfitted`` (the data fitted values, returned on the fit), the
exact LSCV criterion ``slscv`` used by ``lscv.exact``, the density LSCV
``dens_lscv`` (``lscv`` with ``ev = dat()``), and ``lscv_tree`` (``lscv`` with
the default ``ev = rbox()``).

Do not add this directory to ``sys.path``: its top-level ``locfit.py`` would
shadow the compiled module.
"""

from __future__ import annotations

import numpy as np

try:
    from locfit import locfit_fit as _crate_fit
    from locfit import slscv as _crate_slscv
    from locfit import dens_lscv as _crate_dens_lscv
    from locfit import lscv_tree as _crate_lscv_tree
except ImportError as exc:  # the crate is not built in this environment
    _crate_fit = None
    _crate_slscv = None
    _crate_dens_lscv = None
    _crate_lscv_tree = None
    _IMPORT_ERROR = exc

#: R's fit$mi["tg"] for family "qgaussian" with the identity link.
KERNEL_TG = 68

_KT = {"sph": "sph", "spherical": "sph", "prod": "prod", "product": "prod"}


def rep(x, n):
    """R's rep(x, length.out = n)."""
    return np.resize(np.asarray(x, dtype=float), n)


def slscv(x, h):
    """Exact LSCV criterion and degrees of freedom (R's slscv, Gaussian kernel)."""
    if _crate_slscv is None:
        raise ImportError(f"crates/locfit is not built: {_IMPORT_ERROR}")
    return _crate_slscv(np.ascontiguousarray(np.asarray(x, dtype=float).reshape(-1)), float(h))


def dens_lscv(x, nn, fixh, deg, kern):
    """Density LSCV criterion and df at the data (R's lscv default with ev = dat())."""
    if _crate_dens_lscv is None:
        raise ImportError(f"crates/locfit is not built: {_IMPORT_ERROR}")
    return _crate_dens_lscv(np.ascontiguousarray(np.asarray(x, dtype=float).reshape(-1)),
                            nn=float(nn), fixh=float(fixh), deg=int(deg), kern=kern)


def lscv_tree(x, nn, fixh, deg, kern, cut):
    """Density LSCV on the adaptive tree (R's lscv default, ev = rbox(cut))."""
    if _crate_lscv_tree is None:
        raise ImportError(f"crates/locfit is not built: {_IMPORT_ERROR}")
    return _crate_lscv_tree(np.ascontiguousarray(np.asarray(x, dtype=float).reshape(-1)),
                            nn=float(nn), fixh=float(fixh), deg=int(deg), kern=kern,
                            cut=float(cut))


def raw_fit(x, y, *, weights, base, xev, nn, fixh, deg, kern, kt, tree=False, cut=0.8):
    """Call the crate kernel.

    ``xev=None`` fits at the data (R's ev = "data"). ``tree=True`` is R's default
    ev = rbox(cut): the adaptive tree, fitted at its vertices and interpolated.
    """
    if _crate_fit is None:
        raise ImportError(f"crates/locfit is not built: {_IMPORT_ERROR}")
    if kt not in _KT:
        raise NotImplementedError(f"kernel type {kt!r} is not in crates/locfit")
    return _crate_fit(
        x, y, weights=weights, base=base, xev=xev, nn=float(nn),
        fixh=float(fixh), deg=int(deg), kern=kern, kt=_KT[kt],
        scale=None, quasi=True, tree=bool(tree), cut=float(cut),
    )
