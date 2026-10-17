"""M-steps for the EEE, EEV, VEV, and VVV mclust covariance models."""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._mstep_wrap import (
    SIGNIF_XMAX,
    column_major,
    fortran_matrix,
    kernel_call,
    matrix_data,
    prior_params,
    r_warning,
    z_matrix,
)
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options
from mclust.unchol import unchol

__all__ = ["mstepEEE", "mstepEEV", "mstepVEV", "mstepVVV"]


def _inputs(data: Any, z: Any, warn: bool | None):
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = matrix_data(data, "data should be a matrix or a vector")
    n, p = x.shape
    zz = z_matrix(z, n, "row dimension of z should equal data length")
    return bool(warn), x, n, p, zz, zz.shape[1]


def _missing(model: str, x: np.ndarray, z: np.ndarray, prior: Any, warn: bool):
    p = x.shape[1]
    message = "z is missing"
    r_warning(message, warn)
    variance = {
        "modelName": model, "d": p, "G": z.shape[1],
        "sigma": np.full((p, p, z.shape[1]), np.nan),
    }
    if model == "EEE":
        variance["sigma"] = np.full((p, p, z.shape[1]), np.nan)
    parameters = {
        "pro": np.full(z.shape[1], np.nan),
        "mean": np.full((p, z.shape[1]), np.nan),
        "variance": variance,
    }
    return {
        "modelName": model, "prior": prior, "n": x.shape[0], "d": p,
        "G": z.shape[1], "z": z, "parameters": parameters,
        "WARNING": message, "returnCode": 9,
    }


def _prior_args(prior: dict, x: np.ndarray, G: int, model: str):
    pp = prior_params(prior, x, G, model)
    return (
        float(np.asarray(pp["shrinkage"]).reshape(-1)[0]),
        column_major(pp["mean"]),
        column_major(pp["scale"]),
        float(np.asarray(pp["dof"]).reshape(-1)[0]),
    )


def _finish(model, prior, x, z, mu, sigma, pro, extra=None, warning=None, ret=0):
    p, G = x.shape[1], z.shape[1]
    variance = {"modelName": model, "d": p, "G": G, "sigma": sigma}
    if extra:
        variance.update(extra)
    return {
        "modelName": model, "prior": prior, "n": x.shape[0], "d": p,
        "G": G, "z": z,
        "parameters": {"pro": pro, "mean": mu, "variance": variance},
        "WARNING": warning, "returnCode": ret,
    }


def _bad(values):
    return np.any(np.abs(np.asarray(values, dtype=float)) > SIGNIF_XMAX)


def mstepEEE(data: Any, z: Any, prior: dict | None = None,
             warn: bool | None = None) -> dict[str, Any]:
    warn, x, n, p, z, G = _inputs(data, z, warn)
    if np.all(np.isnan(z)):
        return _missing("EEE", x, z, prior, warn)
    if np.any(np.isnan(z)) or np.any((z < 0) | (z > 1)):
        raise ValueError("improper specification of z")
    w = max(n, p, G)
    if prior is None:
        out = kernel_call("mseee", [column_major(x), column_major(z), n, p, G,
                                    [0.0] * w, [0.0] * (p * G),
                                    [0.0] * (p * p), [0.0] * G])
        mu, u, pro = out[6], out[7], out[8]
    else:
        a, pmu, pscale, dof = _prior_args(prior, x, G, "EEE")
        out = kernel_call("mseeep", [column_major(x), column_major(z), n, p, G,
                                     a, pmu, pscale, dof, [0.0] * w,
                                     [0.0] * (p * G), [0.0] * (p * p), [0.0] * G])
        mu, u, pro = out[10], out[11], out[12]
    mu = fortran_matrix(mu, p, G)
    chol = fortran_matrix(u, p, p)
    sigma0 = np.asarray(unchol(chol, upper=True), dtype=float)
    sigma = np.repeat(sigma0[:, :, None], G, axis=2)
    pro = np.asarray(pro, dtype=float)
    warning = None
    ret = 0
    # R checks mu only, with no abs. On failure it sets mu, sigma, Sigma and
    # cholSigma to NA and leaves pro as computed.
    if np.any(mu > SIGNIF_XMAX):
        warning = "cannot compute M-step"
        r_warning(warning, warn)
        mu[:] = np.nan
        sigma[:] = np.nan
        sigma0[:] = np.nan
        chol[:] = np.nan
        ret = -1
    return _finish("EEE", prior, x, z, mu, sigma, pro,
                   {"Sigma": sigma0, "cholSigma": chol}, warning, ret)


def mstepEEV(data: Any, z: Any, prior: dict | None = None,
             warn: bool | None = None) -> dict[str, Any]:
    warn, x, n, p, z, G = _inputs(data, z, warn)
    if np.all(np.isnan(z)):
        return _missing("EEV", x, z, prior, warn)
    if np.any(np.isnan(z)) or np.any((z < 0) | (z > 1)):
        raise ValueError("improper specification of z")
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), G)
    if prior is None:
        out = kernel_call("mseev", [column_major(x), column_major(z), n, p, G,
                                    [0.0] * lwork, lwork, [0.0] * (p * G),
                                    0.0, [0.0] * p, [0.0] * (p * p * G),
                                    [0.0] * G])
        mu, scale, shape, O, pro = out[7], out[8], out[9], out[10], out[11]
    else:
        a, pmu, pscale, dof = _prior_args(prior, x, G, "EEV")
        out = kernel_call("mseevp", [column_major(x), column_major(z), n, p, G,
                                     a, pmu, pscale, dof, [0.0] * lwork, lwork,
                                     [0.0] * (p * G), 0.0, [0.0] * p,
                                     [0.0] * (p * p * G), [0.0] * G])
        mu, scale, shape, O, pro = out[11], out[12], out[13], out[14], out[15]
    mu = fortran_matrix(mu, p, G)
    shape = np.asarray(shape, dtype=float)
    O = np.asarray(O, dtype=float).reshape((p, p, G), order="F").transpose(1, 0, 2)
    scale = float(scale)
    pro = np.asarray(pro, dtype=float)
    sigma = np.empty((p, p, G))
    for g in range(G):
        sigma[:, :, g] = scale * O[:, :, g] @ np.diag(shape) @ O[:, :, g].T
    warning = None
    ret = 0
    if _bad(np.concatenate(([scale], shape, pro))):
        warning = "cannot compute M-step"
        r_warning(warning, warn)
        mu[:] = np.nan; pro[:] = np.nan; O[:] = np.nan
        shape[:] = np.nan; scale = np.nan; sigma[:] = np.nan
        ret = -1
    return _finish("EEV", prior, x, z, mu, sigma, pro,
                   {"scale": scale, "shape": shape, "orientation": O},
                   warning, ret)


def _iter_model(model, data, z, prior, warn, control):
    warn, x, n, p, z, G = _inputs(data, z, warn)
    if np.all(np.isnan(z)):
        return _missing(model, x, z, prior, warn)
    if np.any(np.isnan(z)) or np.any((z < 0) | (z > 1)):
        raise ValueError("improper specification of z")
    if control is None:
        control = em_control()
    itmax = int(np.asarray(control["itmax"]).reshape(-1)[1])
    tol = float(np.asarray(control["tol"]).reshape(-1)[1])
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)
    if prior is None:
        out = kernel_call("msvev", [column_major(x), column_major(z), n, p, G,
                                    [0.0] * lwork, lwork, itmax, tol,
                                    [0.0] * (p * G), [0.0] * G,
                                    [0.0] * (p * G), [0.0] * (p * p * G),
                                    [0.0] * G])
        mu, scale, shape, O, pro = out[9], out[10], out[11], out[12], out[13]
    else:
        a, pmu, pscale, dof = _prior_args(prior, x, G, model)
        out = kernel_call("msvevp", [column_major(x), column_major(z), n, p, G,
                                     a, pmu, pscale, dof, [0.0] * lwork, lwork,
                                     itmax, tol, [0.0] * (p * G), [0.0] * G,
                                     [0.0] * (p * G), [0.0] * (p * p * G),
                                     [0.0] * G])
        mu, scale, shape, O, pro = out[13], out[14], out[15], out[16], out[17]
    mu = fortran_matrix(mu, p, G)
    scale = np.asarray(scale, dtype=float)
    shape = np.asarray(shape, dtype=float)[:p]
    O = np.asarray(O, dtype=float).reshape((p, p, G), order="F").transpose(1, 0, 2)
    pro = np.asarray(pro, dtype=float)
    sigma = np.empty((p, p, G))
    for g in range(G):
        sigma[:, :, g] = scale[g] * O[:, :, g] @ np.diag(shape) @ O[:, :, g].T
    warning = None
    ret = 0
    if _bad(np.concatenate((scale, shape.ravel(), pro))):
        warning = "cannot compute M-step"
        r_warning(warning, warn)
        mu[:] = np.nan; pro[:] = np.nan; O[:] = np.nan
        shape[:] = np.nan; scale[:] = np.nan; sigma[:] = np.nan
        ret = -1
    return _finish(model, prior, x, z, mu, sigma, pro,
                   {"scale": scale, "shape": shape, "orientation": O},
                   warning, ret) | {"control": control}


def mstepVEV(data, z, prior=None, warn=None, control=None):
    return _iter_model("VEV", data, z, prior, warn, control)


def mstepVVV(data: Any, z: Any, prior: dict | None = None,
             warn: bool | None = None) -> dict[str, Any]:
    warn, x, n, p, z, G = _inputs(data, z, warn)
    if np.all(np.isnan(z)):
        # R: variance = list(modelName, d, G, <unnamed sigma NA>, cholsigma = NA)
        out = _missing("VVV", x, z, prior, warn)
        p, G = x.shape[1], z.shape[1]
        out["parameters"]["variance"] = {
            "modelName": "VVV", "d": p, "G": G,
            "cholsigma": np.full((p, p, G), np.nan),
        }
        return out
    if np.any(np.isnan(z)) or np.any((z < 0) | (z > 1)):
        raise ValueError("improper specification of z")
    w = max(n, p, G)
    if prior is None:
        out = kernel_call("msvvv", [column_major(x), column_major(z), n, p, G,
                                    [0.0] * w, [0.0] * (p * G),
                                    [0.0] * (p * p * G), [0.0] * G,
                                    [0.0] * (p * p)])
        mu, u, pro = out[6], out[7], out[8]
    else:
        a, pmu, pscale, dof = _prior_args(prior, x, G, "VVV")
        out = kernel_call("msvvvp", [column_major(x), column_major(z), n, p, G,
                                     a, pmu, pscale, dof, [0.0] * w,
                                     [0.0] * (p * G), [0.0] * (p * p * G),
                                     [0.0] * G, [0.0] * (p * p)])
        mu, u, pro = out[10], out[11], out[12]
    mu = fortran_matrix(mu, p, G)
    U = np.asarray(u, dtype=float).reshape((p, p, G), order="F")
    pro = np.asarray(pro, dtype=float)
    sigma = np.empty((p, p, G))
    for g in range(G):
        sigma[:, :, g] = unchol(U[:, :, g], upper=True)
    warning = None
    ret = 0
    # R checks mu and cholsigma only (no abs, pro untouched on failure).
    if np.any(np.concatenate((mu.ravel(), U.ravel())) > SIGNIF_XMAX):
        warning = "cannot compute M-step"
        r_warning(warning, warn)
        mu[:] = np.nan; U[:] = np.nan; sigma[:] = np.nan
        ret = -1
    # R: variance = list(modelName, d, G, sigma, cholsigma)
    return _finish("VVV", prior, x, z, mu, sigma, pro,
                   {"cholsigma": U}, warning, ret)
