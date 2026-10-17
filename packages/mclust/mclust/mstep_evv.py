"""M-step for the EVV covariance model of mclust 6.1.3 (``mclust2.R``, ``mstepEVV``).

The Fortran ``msevv`` in ``crates/mclust`` computes the weighted scatter,
the SVD of each group, and the common scale. This module is the R wrapper:
the orientation transpose, the scale and shape arithmetic, and the return
codes. A prior is not available for EVV in R, so with a prior the kernel
outputs are the zeros that R's ``temp`` list holds, as in R.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._mstep_wrap import (
    MACHINE_EPS as _EPS,
    SIGNIF_XMAX,
    column_major,
    fortran_matrix,
    kernel_call,
    matrix_data,
    prior_params,
    r_warning,
    z_matrix,
)
from mclust.mclust_options import mclust_options

__all__ = ["mstepEVV"]


def _kernel_outputs(x: np.ndarray, z: np.ndarray, n: int, p: int, G: int, lwork: int) -> dict:
    """The ``.Fortran("msevv", ...)`` call, unpacked by name."""
    out = kernel_call(
        "msevv",
        [
            column_major(x),
            column_major(z),
            n,
            p,
            G,
            [0.0] * (p * G),
            [0.0] * (p * p * G),
            [0.0] * (p * p * G),
            [0.0] * G,
            [0.0] * (p * G),
            [0.0] * G,
            lwork,
            0,
            _EPS,
        ]
    )
    return {
        "mu": out[5],
        "O": out[6],
        "shape_o": out[7],
        "scale": out[8],
        "shape": out[9],
        "pro": out[10],
        "info": int(out[12]),
    }


def _zero_outputs(p: int, G: int) -> dict:
    """R's ``temp`` list for the prior branch: every output is zero, and ``info`` is FALSE."""
    return {
        "mu": [0.0] * (p * G),
        "O": [0.0] * (p * p * G),
        "shape_o": [0.0] * (p * p * G),
        "scale": [0.0] * G,
        "shape": [0.0] * (p * G),
        "pro": [0.0] * G,
        "info": 0,
    }


def mstepEVV(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
) -> dict[str, Any]:
    """M-step for the EVV model: equal volume, variable shape and orientation."""
    if warn is None:
        warn = bool(mclust_options("warn"))

    x = matrix_data(data, "data should be a matrix or a vector")
    n, p = x.shape
    z = z_matrix(z, n, "row dimension of z should equal data length")
    G = z.shape[1]

    if np.all(np.isnan(z)):
        message = "z is missing"
        r_warning(message, warn)
        variance = {
            "modelName": "EVV",
            "d": p,
            "G": G,
            "scale": np.nan,
            "shape": np.full(p, np.nan),
            "orientation": np.full((p, p, G), np.nan),
        }
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full((p, G), np.nan),
            "variance": variance,
        }
        return {
            "modelName": "EVV",
            "prior": prior,
            "n": n,
            "d": p,
            "G": G,
            "z": z,
            "parameters": parameters,
            "WARNING": message,
            "returnCode": 9,
        }

    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")

    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), G)

    if prior is None:
        temp = _kernel_outputs(x, z, n, p, G, lwork)
    else:
        prior_params(prior, x, G, "EVV")
        r_warning("EVV model is not available with prior", warn)
        temp = _zero_outputs(p, G)

    lapack_info = temp["info"]
    mu = fortran_matrix(temp["mu"], p, G)
    # aperm(array(temp$O, c(p,p,G)), c(2,1,3))
    O = np.asarray(temp["O"], dtype=float).reshape((p, p, G), order="F").transpose(1, 0, 2)
    shape_o = np.asarray(temp["shape_o"], dtype=float).reshape((p, p, G), order="F")
    scale = float(np.asarray(temp["scale"], dtype=float)[0])  # lambda
    shape = fortran_matrix(temp["shape"], p, G)
    pro = np.asarray(temp["pro"], dtype=float)
    WARNING: str | None = None

    if lapack_info:
        if lapack_info > 0:
            WARNING = "LAPACK DGESVD fails to converge"
            ret = -4
        else:
            WARNING = "input error for LAPACK DGESVD"
            ret = -5
        r_warning(WARNING, warn)
        O[:] = np.nan
        shape[:] = np.nan
        scale = np.nan
        sigma = np.full((p, p, G), np.nan)
    elif np.any(np.abs(np.concatenate(([scale], shape.ravel()))) > SIGNIF_XMAX):
        WARNING = "cannot compute M-step"
        r_warning(WARNING, warn)
        mu[:] = np.nan
        pro[:] = np.nan
        scale = np.nan
        shape[:] = np.nan
        O[:] = np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -1
    else:
        sigma = scale * shape_o
        ret = 0

    variance = {
        "modelName": "EVV",
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": "EVV",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "WARNING": WARNING,
        "returnCode": ret,
    }
