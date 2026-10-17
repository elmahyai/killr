"""kdeb: kernel density bandwidth selection (R locfit 1.5-9.12 `kdeb`).

R calls the C routine `kdeb` through `.C("kdeb")`, which runs locfit's
`kdeselect` (band.c). The port is the `kdeb` entry in crates/locfit, exposed
as `kdeb_bandwidth`. The R-side defaults are kept: `sd` is the sample standard
deviation, `h0 = 0.01 * sd`, `h1 = sd`, and both are scaled by `gf`.

The compiled module is imported as `locfit`. Do not put packages/locfit on
sys.path, because its top-level `locfit.py` would shadow the crate.
"""

from __future__ import annotations

import numpy as np

import locfit as _crate


def kdeb(x, h0=None, h1=None, meth=("AIC", "LCV", "LSCV", "BCV", "SJPI", "GKK"),
         kern="gauss", gf=2.5):
    x = np.ascontiguousarray(np.asarray(x, dtype=float).reshape(-1))
    sd = float(np.sqrt(np.var(x, ddof=1)))
    if h0 is None:
        h0 = 0.01 * sd
    if h1 is None:
        h1 = sd
    names = [str(m) for m in (meth if isinstance(meth, (list, tuple)) else [meth])]
    bands = _crate.kdeb_bandwidth(x, float(gf * h0), float(gf * h1), names, str(kern))
    return dict(zip(names, np.asarray(bands, dtype=float).tolist()))


__all__ = ["kdeb"]
