"""Exact conditional Cox fit (survival coxexact.c via Rust)."""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    from coxexact import coxexact_py as _coxexact
except ImportError:
    _coxexact = None


def coxexact_fit(
    *,
    maxiter: int,
    y: np.ndarray,
    x: np.ndarray,
    offset: np.ndarray,
    strata: np.ndarray,
    init: np.ndarray | None,
    eps: float,
    toler_chol: float,
    rescale: np.ndarray,
    means: np.ndarray,
) -> dict[str, Any]:
    if _coxexact is None:
        raise RuntimeError("install the coxexact Rust extension")
    nvar = x.shape[1]
    if init is None:
        init_scaled = np.zeros(nvar, dtype=float)
    else:
        init_scaled = np.asarray(init, dtype=float).reshape(-1) * np.asarray(rescale, dtype=float)
    beta, u, imat, loglik_pack, iter_ = _coxexact(
        int(maxiter),
        np.asarray(y, dtype=float),
        np.asarray(x, dtype=float),
        np.asarray(offset, dtype=float),
        np.asarray(strata, dtype=np.int32).copy(),
        init_scaled,
        float(eps),
        float(toler_chol),
    )
    loglik = np.array([loglik_pack[0], loglik_pack[1]], dtype=float)
    sctest = float(loglik_pack[2])
    flag = int(loglik_pack[3])
    iter_out = int(loglik_pack[4])
    coef_scaled = np.asarray(beta, dtype=float)
    var = np.asarray(imat, dtype=float)
    if flag < nvar:
        which_sing = np.diag(var) == 0
    else:
        which_sing = np.zeros(nvar, dtype=bool)
    coef_scaled = coef_scaled.copy()
    coef_scaled[which_sing] = np.nan
    scmat = np.diag(1.0 / np.asarray(rescale, dtype=float))
    var_out = scmat @ var @ scmat
    coef = coef_scaled / np.asarray(rescale, dtype=float)
    return {
        "coef": coef,
        "var": var_out,
        "loglik": loglik,
        "sctest": sctest,
        "iter": iter_out,
        "flag": flag,
        "which_sing": which_sing,
        "means": np.asarray(means, dtype=float),
        "u": np.asarray(u, dtype=float),
    }
