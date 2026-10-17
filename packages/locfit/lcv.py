"""Leave-one-out criterion used by locfit plotting helpers."""
from __future__ import annotations
import numpy as np
from .locfit_raw import locfit_raw

def lcv(x, y=None, **kwargs):
    if y is None and isinstance(x, dict):
        y, x = x["y"], x["x"]
    x = np.asarray(x, dtype=float)
    if x.ndim == 1: x = x[:, None]
    y = np.asarray(y, dtype=float).reshape(-1)
    fit = locfit_raw(x, y, **kwargs)
    th = np.asarray(fit["fitted"], dtype=float)
    hii = np.empty(len(y))
    for i in range(len(y)):
        e = np.zeros(len(y)); e[i] = 1.0
        hii[i] = locfit_raw(x, e, **kwargs)["fitted"][i]
    cv_th = th - hii * (y - th)
    dp = fit["dp"]
    return {"lik": float(dp["lk"]), "infl": float(dp["df1"]),
            "vari": float(dp["df2"]), "cv": float(np.sum((y - cv_th) ** 2))}

__all__ = ["lcv"]
