"""EM translations for the EEE and EEV covariance models.

The numerical iterations are the ``meeee`` and ``meeev`` kernels.  Their
arguments and returned work arrays are kept in the same order as R's
``.Fortran`` calls.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._me_e_family import (
    SIGNIF_XMAX,
    below_threshold,
    column_major,
    first,
    fortran_matrix,
    groups_and_vinv,
    iteration_status,
    kernels,
    logical,
    matrix_data,
    prior_params,
    r_warning,
    z_matrix,
)
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options

__all__ = ["meEEE", "meEEV"]


def _common(data: Any, z: Any, Vinv: Any) -> tuple[np.ndarray, np.ndarray, int, Any]:
    x = matrix_data(data, "data should be in the form of a matrix")
    n = x.shape[0]
    zz = z_matrix(z, n, "data and z should have the same row dimension")
    G, Vinv = groups_and_vinv(x, zz.shape[1], Vinv)
    return x, zz, G, Vinv


def _missing(kind: str, x: np.ndarray, z: np.ndarray, G: int, Vinv: Any, control: dict, prior: Any, warn: bool) -> dict:
    message = "z is missing"
    r_warning(message, warn)
    p = x.shape[1]
    variance = {"modelName": kind, "d": p, "G": G}
    if kind == "EEE":
        variance.update({"sigma": np.full((p, p, G), np.nan), "Sigma": np.full((p, p), np.nan)})
    else:
        variance.update({
            "sigma": np.full((p, p, G), np.nan),
            "scale": np.nan,
            "shape": np.full(p, np.nan),
            "orientation": np.full((p, p, G), np.nan),
        })
    return {
        "modelName": kind, "prior": prior, "n": x.shape[0], "d": p, "G": G,
        "z": z, "parameters": {"pro": np.full(G, np.nan), "mean": np.full((p, G), np.nan), "variance": variance, "Vinv": Vinv},
        "control": control, "loglik": np.nan, "WARNING": message, "returnCode": 9,
    }


def _fit(kind: str, data: Any, z: Any, prior: dict | None, control: dict | None, Vinv: Any, warn: bool | None) -> dict:
    if control is None:
        control = em_control()
    if warn is None:
        warn = mclust_options("warn")
    warn = bool(warn)
    x, zz, G, Vinv = _common(data, z, Vinv)
    n, p = x.shape
    K = zz.shape[1]
    if np.all(np.isnan(zz)):
        return _missing(kind, x, zz, G, Vinv, control, prior, warn)
    if np.isnan(zz).any() or (zz < 0).any() or (zz > 1).any():
        raise ValueError("improper specification of z")

    eqpro = logical(control["equalPro"])
    itmax, tol, eps = int(first(control["itmax"])), float(first(control["tol"])), float(first(control["eps"]))
    vinv_arg = -1.0 if Vinv is None else float(Vinv)
    xl, zl = column_major(x), column_major(zz)
    if kind == "EEE":
        args = [eqpro, xl, n, p, G, vinv_arg, zl, itmax, tol, eps,
                [0.0] * (p * G), [0.0] * (p * p), [0.0] * K, [0.0] * p]
        if prior is not None:
            pp = prior_params(prior, x, G, kind)
            args = [eqpro, xl, n, p, G, vinv_arg, float(first(pp["shrinkage"])),
                    column_major(pp["mean"]), column_major(pp["scale"]), float(first(pp["dof"])), zl,
                    itmax, tol, eps, [0.0] * (p * G), [0.0] * (p * p), [0.0] * K, [0.0] * p]
        out = (kernels().meeee(args) if prior is None else kernels().meeeep(args))
        off = 0 if prior is None else 4
        z_out, its, err, hood = out[6 + off], out[7 + off], out[8 + off], out[9 + off]
        mu = fortran_matrix(out[10 + off], p, G)
        U = fortran_matrix(out[11 + off], p, p)
        pro = np.asarray(out[12 + off], dtype=float)
        Sigma = U.T @ U
        sigma = np.repeat(Sigma[:, :, None], G, axis=2)
        shape = orientation = None
    else:
        lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)
        args = [eqpro, xl, n, p, G, vinv_arg, zl, itmax, tol, eps, lwork,
                [0.0] * (p * G), 0.0, [0.0] * p, [0.0] * (p * p * G),
                [0.0] * K, [0.0] * lwork, [0.0] * p]
        if prior is not None:
            pp = prior_params(prior, x, G, kind)
            args = [eqpro, xl, n, p, G, vinv_arg, float(first(pp["shrinkage"])),
                    column_major(pp["mean"]), column_major(pp["scale"]), float(first(pp["dof"])), zl,
                    itmax, tol, eps, lwork, [0.0] * (p * G), 0.0, [0.0] * p,
                    [0.0] * (p * p * G), [0.0] * K, [0.0] * lwork, [0.0] * p]
        out = (kernels().meeev(args) if prior is None else kernels().meeevp(args))
        off = 0 if prior is None else 4
        z_out, its, err, lwork = out[6 + off], out[7 + off], out[8 + off], out[9 + off]
        mu = fortran_matrix(out[11 + off], p, G)
        scale = float(out[12 + off])
        shape = np.asarray(out[13 + off], dtype=float)
        orientation = np.asarray(out[14 + off], dtype=float).reshape((p, p, G), order="F").transpose(1, 0, 2)
        pro = np.asarray(out[15 + off], dtype=float)
        sigma = np.empty((p, p, G))
        for g in range(G):
            sigma[:, :, g] = scale * orientation[:, :, g] @ np.diag(shape) @ orientation[:, :, g].T
        Sigma = None
        hood = float(out[9 + off])

    z_out = np.asarray(z_out, dtype=float).reshape((n, K), order="F")
    loglik = float(out[9 + off])
    warning = None
    if loglik > SIGNIF_XMAX:
        warning, ret = "singular covariance", -1
        r_warning(warning, warn)
        z_out[:] = np.nan; mu[:] = np.nan; pro[:] = np.nan; sigma[:] = np.nan; loglik = np.nan
        if kind == "EEE": Sigma[:] = np.nan
        else: scale = np.nan; shape[:] = np.nan; orientation[:] = np.nan
    elif loglik < -SIGNIF_XMAX:
        warning, ret = below_threshold(bool(first(control["equalPro"])), warn)
        z_out[:] = np.nan; mu[:] = np.nan; pro[:] = np.nan; sigma[:] = np.nan; loglik = np.nan
        if kind == "EEE": Sigma[:] = np.nan
        else: scale = np.nan; shape[:] = np.nan; orientation[:] = np.nan
    else:
        its, ret, warning = iteration_status(int(its), itmax, warn)
    variance = {"modelName": kind, "d": p, "G": G, "sigma": sigma}
    if kind == "EEE":
        variance.update({"Sigma": Sigma, "cholsigma": U})
    else:
        variance.update({"scale": scale, "shape": shape, "orientation": orientation})
    return {"modelName": kind, "prior": prior, "n": n, "d": p, "G": G, "z": z_out,
            "parameters": {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv},
            "control": control, "loglik": loglik, "info": {"iterations": int(its), "error": float(err)},
            "WARNING": warning, "returnCode": ret}


def meEEE(data, z, prior=None, control=None, Vinv=None, warn=None, **kwargs):
    return _fit("EEE", data, z, prior, control, Vinv, warn)


def meEEV(data, z, prior=None, control=None, Vinv=None, warn=None, **kwargs):
    return _fit("EEV", data, z, prior, control, Vinv, warn)
