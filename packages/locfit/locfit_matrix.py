"""locfit.matrix: the design data behind a fit, as R's locfit.matrix returns it.

R reads the data from the fit's stored call and frame. The translated fits
keep the same inputs in ``fit["data"]``, so ``data`` is not needed here.
``sc`` is the weight vector for the families whose ``mi["tg"] %% 64`` is in
5:8, 11 or 12, and 1 otherwise, as in R.
"""

from __future__ import annotations


def locfit_matrix(fit, data=None):
    d = fit["data"]
    tg = int(fit["mi"]["tg"])
    sc = d["weights"] if (tg % 64) in (5, 6, 7, 8, 11, 12) else 1.0
    return {"x": d["x"], "y": d["y"], "w": d["weights"], "sc": sc,
            "ce": d["cens"], "base": d["base"]}
