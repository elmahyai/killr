"""Fixed parameters for the sim proofs (mclust 6.1.3).

The same literal numbers are in sim_fixtures.R. A matrix's columns are the
components. ``_m`` fills column by column, as R's ``matrix`` does.
"""

from __future__ import annotations

import copy

import numpy as np


def _m(vals, nrow, ncol):
    return np.array(vals, dtype=float).reshape((nrow, ncol), order="F")


SIM_MU = _m([0, 2, -1, 1, 0.5, 1.5, -1, -0.5, 0.25], 3, 3)
SIM_PRO = np.array([0.2, 0.3, 0.5])
SIM_O1 = _m([0.6, 0.8, 0, -0.64, 0.48, -0.6, -0.48, 0.36, 0.8], 3, 3)
SIM_O2 = _m([0, 1, 0, 0, 0, 1, 1, 0, 0], 3, 3)
SIM_O3 = _m([1, 0, 0, 0, 0.6, -0.8, 0, 0.8, 0.6], 3, 3)
SIM_OARR = np.stack([SIM_O1, SIM_O2, SIM_O3], axis=2)
SIM_SHAPE_D = np.array([1.0, 2.0, 0.5])
SIM_SCALE_G = np.array([0.5, 1.5, 0.8])
SIM_SHAPE_DG = _m([1, 2, 0.5, 1.5, 1, 2, 0.8, 0.6, 1.2], 3, 3)
SIM_SCALE_1 = 1.4
SIM_SIGMA = np.stack(
    [
        _m([2, 0.3, 0.1, 0.3, 1.5, -0.2, 0.1, -0.2, 1], 3, 3),
        _m([1, 0, 0, 0, 2, 0.5, 0, 0.5, 1.2], 3, 3),
        _m([0.7, -0.1, 0.05, -0.1, 0.9, 0.2, 0.05, 0.2, 1.5], 3, 3),
    ],
    axis=2,
)
SIM_SIGMASQ = np.array([0.5, 1.5, 0.8])


def _upper_chol(sigma):
    """R ``chol``: the upper triangular U with t(U) %*% U = sigma."""
    return np.linalg.cholesky(sigma).T


def sim_params(model: str, use_chol: bool = False) -> dict:
    """The parameter dict for one model, as R's ``sim_params`` builds it."""
    if model == "VEV":
        var = {"shape": SIM_SHAPE_D, "scale": SIM_SCALE_G, "orientation": SIM_OARR}
    elif model == "VII":
        var = {"sigmasq": SIM_SIGMASQ}
    elif model == "VVI":
        var = {"shape": SIM_SHAPE_DG, "scale": SIM_SCALE_G}
    elif model == "VVV":
        if use_chol:
            chol = np.stack([_upper_chol(SIM_SIGMA[:, :, k]) for k in range(3)], axis=2)
            var = {"cholsigma": chol}
        else:
            var = {"sigma": SIM_SIGMA}
    elif model == "EVV":
        var = {"shape": SIM_SHAPE_DG, "scale": SIM_SCALE_1, "orientation": SIM_OARR}
    elif model == "VEE":
        var = {"shape": SIM_SHAPE_D, "scale": SIM_SCALE_G, "orientation": SIM_O1}
    elif model == "EVE":
        var = {"shape": SIM_SHAPE_DG, "scale": SIM_SCALE_1, "orientation": SIM_O1}
    elif model == "VVE":
        var = {"shape": SIM_SHAPE_DG, "scale": SIM_SCALE_G, "orientation": SIM_O1}
    else:
        raise ValueError(model)
    return {"pro": SIM_PRO.copy(), "mean": SIM_MU.copy(), "variance": var}


def sim_params_missing(model: str) -> dict:
    """The same parameters with the mean missing (the R missing-parameter branch)."""
    p = copy.deepcopy(sim_params(model))
    p["mean"] = np.nan
    return p
