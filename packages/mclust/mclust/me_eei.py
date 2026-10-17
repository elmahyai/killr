"""Translation of mclust ``meEEI``: EM with diagonal covariance, equal volume and shape."""

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
    r_diag,
    r_warning,
    z_matrix,
)
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options


def meEEI(
    data: Any,
    z: Any,
    prior: dict | None = None,
    control: dict | None = None,
    Vinv: float | None = None,
    warn: bool | None = None,
) -> dict[str, Any]:
    if control is None:
        control = em_control()
    if warn is None:
        warn = mclust_options("warn")

    x = matrix_data(data, "data  should be in the form of a matrix")
    n, p = x.shape
    z = z_matrix(z, n, "data and z should have the same row dimension")
    K = z.shape[1]
    G, Vinv = groups_and_vinv(x, K, Vinv)

    if np.all(np.isnan(z)):
        message = "z is missing"
        r_warning(message, warn)
        variance = {"modelName": "EEI", "d": p, "G": G, "scale": np.nan, "shape": np.full(p, np.nan)}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full((p, G), np.nan),
            "variance": variance,
            "Vinv": Vinv,
        }
        return {
            "modelName": "EEI",
            "prior": prior,
            "n": n,
            "d": p,
            "G": G,
            "z": z,
            "parameters": parameters,
            "control": control,
            "loglik": np.nan,
            "WARNING": message,
            "returnCode": 9,
        }

    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")

    eqpro = logical(control["equalPro"])
    itmax = int(first(control["itmax"]))
    tol = float(first(control["tol"]))
    eps = float(first(control["eps"]))
    vinv_arg = -1.0 if Vinv is None else float(Vinv)
    x_list = column_major(x)
    z_list = column_major(z)
    lib = kernels()

    if prior is None:
        out = lib.meeei(
            [
                eqpro,
                x_list,
                n,
                p,
                G,
                vinv_arg,
                z_list,
                itmax,
                tol,
                eps,
                [0.0] * (p * G),
                0.0,
                [0.0] * p,
                [0.0] * K,
            ]
        )
        z_out, its, err, loglik = out[6], out[7], out[8], out[9]
        mu, scale, shape, pro = out[10], out[11], out[12], out[13]
    else:
        pp = prior_params(prior, x, G, "EEI")
        out = lib.meeeip(
            [
                eqpro,
                x_list,
                n,
                p,
                G,
                vinv_arg,
                float(first(pp["shrinkage"])),
                column_major(pp["mean"]),
                float(first(pp["scale"])),
                float(first(pp["dof"])),
                z_list,
                itmax,
                tol,
                eps,
                [0.0] * (p * G),
                0.0,
                [0.0] * p,
                [0.0] * K,
            ]
        )
        z_out, its, err, loglik = out[10], out[11], out[12], out[13]
        mu, scale, shape, pro = out[14], out[15], out[16], out[17]

    z = np.asarray(z_out, dtype=float).reshape((n, K), order="F")
    mu = fortran_matrix(mu, p, G)
    pro = np.asarray(pro, dtype=float)
    shape = np.asarray(shape, dtype=float)
    its = int(its)
    loglik = float(loglik)
    scale = float(scale)

    WARNING: str | None = None
    if loglik > SIGNIF_XMAX:
        WARNING = "singular covariance"
        r_warning(WARNING, warn)
        sigma = np.full((p, p, G), np.nan)
        Sigma = np.full((p, p), np.nan)
        mu[:] = np.nan
        pro[:] = np.nan
        z[:] = np.nan
        loglik = np.nan
        shape[:] = np.nan
        ret = -1
    elif loglik < -SIGNIF_XMAX:
        WARNING, ret = below_threshold(bool(first(control["equalPro"])), warn)
        sigma = np.full((p, p, G), np.nan)
        Sigma = np.full((p, p), np.nan)
        mu[:] = np.nan
        pro[:] = np.nan
        z[:] = np.nan
        loglik = np.nan
        shape[:] = np.nan
    else:
        Sigma = r_diag(scale * shape)
        sigma = np.zeros((p, p, G), order="F")
        for k in range(G):
            sigma[:, :, k] = Sigma
        its, ret, WARNING = iteration_status(its, itmax, warn)

    variance = {
        "modelName": "EEI",
        "d": p,
        "G": G,
        "sigma": sigma,
        "Sigma": Sigma,
        "scale": scale,
        "shape": shape,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return {
        "modelName": "EEI",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "loglik": loglik,
        "info": {"iterations": its, "error": float(err)},
        "WARNING": WARNING,
        "returnCode": ret,
    }
