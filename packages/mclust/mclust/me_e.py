"""Translation of mclust ``meE``: one-dimensional EM with equal variance."""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._me_e_family import (
    SIGNIF_XMAX,
    below_threshold,
    column_major,
    first,
    groups_and_vinv,
    iteration_status,
    kernels,
    logical,
    prior_params,
    r_warning,
    z_matrix,
)
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options


def meE(
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

    arr = np.asarray(data, dtype=float)
    if not (arr.ndim == 1 or (arr.ndim == 2 and arr.shape[1] == 1)):
        raise ValueError("data must be 1 dimensional")
    x = arr.ravel()
    n = x.size
    z = z_matrix(z, n, "row dimension of z should equal length of data")
    K = z.shape[1]
    G, Vinv = groups_and_vinv(x, K, Vinv)

    if np.all(np.isnan(z)):
        message = "z is missing"
        r_warning(message, warn)
        variance = {"modelName": "E", "d": 1, "G": G, "sigmasq": np.nan}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full(G, np.nan),
            "variance": variance,
            "Vinv": Vinv,
        }
        return {
            "modelName": "E",
            "prior": prior,
            "n": n,
            "d": 1,
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
    x_list = x.tolist()
    z_list = column_major(z)
    lib = kernels()

    if prior is None:
        out = lib.me1e(
            [eqpro, x_list, n, G, vinv_arg, z_list, itmax, tol, eps, [0.0] * G, 0.0, [0.0] * K]
        )
        z_out, its, err, loglik, mu, sigmasq, pro = out[5], out[6], out[7], out[8], out[9], out[10], out[11]
    else:
        pp = prior_params(prior, x, G, "E")
        out = lib.me1ep(
            [
                eqpro,
                x_list,
                n,
                G,
                vinv_arg,
                float(first(pp["shrinkage"])),
                float(first(pp["mean"])),
                float(first(pp["scale"])),
                float(first(pp["dof"])),
                z_list,
                itmax,
                tol,
                eps,
                [0.0] * G,
                0.0,
                [0.0] * K,
            ]
        )
        z_out, its, err, loglik, mu, sigmasq, pro = out[9], out[10], out[11], out[12], out[13], out[14], out[15]

    z = np.asarray(z_out, dtype=float).reshape((n, K), order="F")
    mu = np.asarray(mu, dtype=float)
    pro = np.asarray(pro, dtype=float)
    its = int(its)
    loglik = float(loglik)
    sigmasq = float(sigmasq)
    eps_floor = max(eps, 0.0)

    WARNING: str | None = None
    if loglik > SIGNIF_XMAX or sigmasq <= eps_floor:
        WARNING = "sigma-squared falls below threshold"
        r_warning(WARNING, warn)
        mu[:] = np.nan
        pro[:] = np.nan
        sigmasq = np.nan
        z[:] = np.nan
        loglik = np.nan
        ret = -1
    elif loglik < -SIGNIF_XMAX:
        WARNING, ret = below_threshold(bool(first(control["equalPro"])), warn)
        mu[:] = np.nan
        pro[:] = np.nan
        sigmasq = np.nan
        z[:] = np.nan
        loglik = np.nan
    else:
        its, ret, WARNING = iteration_status(its, itmax, warn)

    variance = {"modelName": "E", "d": 1, "G": G, "sigmasq": sigmasq}
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return {
        "modelName": "E",
        "prior": prior,
        "n": n,
        "d": 1,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "loglik": loglik,
        "info": {"iterations": its, "error": float(err)},
        "WARNING": WARNING,
        "returnCode": ret,
    }
