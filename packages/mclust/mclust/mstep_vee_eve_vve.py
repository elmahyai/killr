"""M-step for the VEE, EVE, and VVE covariance models of mclust 6.1.3 (``mclust2.R``).

The iterative Fortran kernels ``msvee``, ``mseve``, and ``msvve`` in
``crates/mclust`` compute the weighted scatter and the shape and orientation
iterations. This module is the R wrapper: the initial values R passes, the
orientation and SVD post-processing, the sigma arithmetic, and the return
codes. The kernels take the same arguments, in the same order, as R's
``.Fortran`` calls.
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
    pick_second as _pick,
    prior_params,
    r_warning,
    z_matrix,
)
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options

__all__ = ["mstepVEE", "mstepEVE", "mstepVVE"]


def _missing_z(model: str, p: int, G: int, n: int, z: np.ndarray, prior: Any,
               control: Any, warn: bool) -> dict[str, Any]:
    """The return when every entry of ``z`` is missing."""
    message = "z is missing"
    r_warning(message, warn)
    variance = {
        "modelName": model,
        "d": p,
        "G": G,
        "scale": np.full(G, np.nan),
        "shape": np.full(p, np.nan),
        "orientation": np.full((p, p, G), np.nan),
    }
    parameters = {
        "pro": np.full(G, np.nan),
        "mean": np.full((p, G), np.nan),
        "variance": variance,
    }
    return {
        "modelName": model,
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


def _check_inputs(data: Any, z: Any, warn: bool | None):
    if warn is None:
        warn = bool(mclust_options("warn"))
    x = matrix_data(data, "data should be a matrix or a vector")
    n, p = x.shape
    z = z_matrix(z, n, "row dimension of z should equal data length")
    G = z.shape[1]
    return warn, x, n, p, z, G


def _iteration_status(niterin: int, itmax: int, warn: bool) -> tuple[int, str | None]:
    """The inner-iteration limit check at the end of the normal branch."""
    if niterin >= itmax:
        message = "inner iteration limit reached"
        r_warning(message, warn)
        return -niterin, message
    return niterin, None


def _sigma_from_shape_o(shape_o: np.ndarray, scale: np.ndarray, p: int, G: int) -> np.ndarray:
    """``sweep(array(shape.o, c(p,p,G)), 3, FUN = "*", STATS = scale)``."""
    sigma = np.empty((p, p, G))
    for g in range(G):
        sigma[:, :, g] = shape_o * scale[g]
    return sigma


def _sigma_from_orientation(O: np.ndarray, shape: np.ndarray, scale: Any,
                            p: int, G: int, per_group_scale: bool) -> np.ndarray:
    """``scale * O %*% diag(shape[,g]) %*% t(O)`` for each group ``g``."""
    sigma = np.empty((p, p, G))
    for g in range(G):
        s = scale[g] if per_group_scale else scale
        sigma[:, :, g] = s * O @ np.diag(shape[:, g]) @ O.T
    return sigma


# ---------------------------------------------------------------------------
# VEE
# ---------------------------------------------------------------------------


def mstepVEE(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
    control: dict | None = None,
) -> dict[str, Any]:
    """M-step for the VEE model: equal orientation, variable volume and shape."""
    warn, x, n, p, z, G = _check_inputs(data, z, warn)

    if np.all(np.isnan(z)):
        return _missing_z("VEE", p, G, n, z, prior, control, warn)

    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")

    if control is None:
        control = em_control()
    itmax = int(_pick(control["itmax"]))
    tol = _pick(control["tol"])
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)

    if prior is None:
        out = kernel_call(
            "msvee",
            [
                column_major(x),
                column_major(z),
                n,
                p,
                G,
                [0.0] * (p * G),
                [0.0] * (p * p * G),
                [0.0] * (p * p),
                [1.0] * G,
                [0.0] * G,
                lwork,
                0,
                itmax,
                tol,
                0,
                0.0,
            ]
        )
        temp = {
            "mu": out[5],
            "C": out[7],
            "scale": out[8],
            "pro": out[9],
            "info": int(out[11]),
            "niterin": int(out[14]),
            "errin": float(out[15]),
        }
    else:
        prior_params(prior, x, G, "VEE")
        r_warning("VEE model is not available with prior", warn)
        temp = {
            "mu": [0.0] * (p * G),
            "C": [0.0] * (p * p),
            "scale": [0.0] * G,
            "pro": [0.0] * G,
            "info": 0,
            "niterin": 0,
            "errin": 0.0,
        }

    lapack_info = temp["info"]
    errin = temp["errin"]
    niterin = temp["niterin"]
    mu = fortran_matrix(temp["mu"], p, G)
    scale = np.asarray(temp["scale"], dtype=float)
    shape_o = fortran_matrix(temp["C"], p, p)
    # svd(shape.o, nu = 0): d are the singular values, v the right singular vectors.
    _, d, vt = np.linalg.svd(shape_o)
    shape = d.astype(float)
    O = vt.T
    pro = np.asarray(temp["pro"], dtype=float)
    WARNING: str | None = None

    if lapack_info:
        if lapack_info > 0:
            WARNING = "LAPACK DSYEV or DPOTRI fails to converge"
        else:
            WARNING = "input error for LAPACK DPOTRF, DSYEV or DPOTRI"
        r_warning(WARNING, warn)
        O[:] = np.nan
        shape[:] = np.nan
        scale[:] = np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -9
    elif np.any(np.concatenate([scale, shape]) > SIGNIF_XMAX):
        WARNING = "cannot compute M-step"
        r_warning(WARNING, warn)
        mu[:] = np.nan
        pro[:] = np.nan
        O[:] = np.nan
        shape[:] = np.nan
        scale[:] = np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -1
    else:
        sigma = _sigma_from_shape_o(shape_o, scale, p, G)
        niterin, WARNING = _iteration_status(niterin, itmax, warn)
        ret = 2

    info = {"iteration": niterin, "error": errin}
    variance = {
        "modelName": "VEE",
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": "VEE",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "info": info,
        "WARNING": WARNING,
        "returnCode": ret,
    }


# ---------------------------------------------------------------------------
# EVE and VVE share the same iterative call shape; they differ in the kernel,
# in whether scale is one value or G values, and in how sigma is formed.
# ---------------------------------------------------------------------------


def _iterative_orientation_call(kernel_name: str, x, z, n, p, G, lwork, itmax, tol, scale_init):
    """The ``.Fortran("mseve" | "msvve", ...)`` call for EVE or VVE."""
    return kernel_call(
        kernel_name,
        [
            column_major(x),
            column_major(z),
            n,
            p,
            G,
            [0.0] * (p * G),
            [0.0] * (p * p * G),
            column_major(np.eye(p)),
            scale_init,
            column_major(np.ones((p, G))),
            [0.0] * G,
            lwork,
            0,
            itmax,
            tol,
            0,
            0.0,
            _EPS,
        ]
    )


def _mstep_orientation_model(model: str, data: Any, z: Any, prior: Any, warn: bool | None,
                             control: Any) -> dict[str, Any]:
    warn, x, n, p, z, G = _check_inputs(data, z, warn)

    if np.all(np.isnan(z)):
        return _missing_z(model, p, G, n, z, prior, control, warn)

    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")

    if control is None:
        control = em_control()
    itmax = int(_pick(control["itmax"]))
    tol = _pick(control["tol"])
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)

    per_group = model == "VVE"
    kernel_name = "msvve" if per_group else "mseve"
    scale_init: Any = [1.0] * G if per_group else 1.0

    if prior is None:
        out = _iterative_orientation_call(kernel_name, x, z, n, p, G, lwork, itmax, tol, scale_init)
        temp = {
            "mu": out[5],
            "O": out[7],
            "scale": out[8],
            "shape": out[9],
            "pro": out[10],
            "info": int(out[12]),
            "niterin": int(out[15]),
            "errin": float(out[16]),
        }
    else:
        prior_params(prior, x, G, model)
        r_warning(f"{model} model is not available with prior", warn)
        temp = {
            "mu": [0.0] * (p * G),
            "O": [0.0] * (p * p),
            "scale": [0.0] * G if per_group else 0.0,
            "shape": [0.0] * (p * G),
            "pro": [0.0] * G,
            "info": 0,
            "niterin": 0,
            "errin": 0.0,
        }

    lapack_info = temp["info"]
    errin = temp["errin"]
    niterin = temp["niterin"]
    mu = fortran_matrix(temp["mu"], p, G)
    # t(matrix(temp$O, p, p))
    O = fortran_matrix(temp["O"], p, p).T
    shape = fortran_matrix(temp["shape"], p, G)
    if per_group:
        scale = np.asarray(temp["scale"], dtype=float)
    else:
        scale = float(temp["scale"])
    pro = np.asarray(temp["pro"], dtype=float)
    WARNING: str | None = None

    if lapack_info:
        if lapack_info > 0:
            WARNING = "LAPACK DSYEV or DGESVD fails to converge"
        else:
            WARNING = "input error for LAPACK DSYEV or DGESVD"
        r_warning(WARNING, warn)
        O[:] = np.nan
        shape[:] = np.nan
        scale = np.full(G, np.nan) if per_group else np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -9
    elif np.any(np.concatenate([np.atleast_1d(scale).ravel(), shape.ravel()]) > SIGNIF_XMAX):
        WARNING = "cannot compute M-step"
        r_warning(WARNING, warn)
        mu[:] = np.nan
        pro[:] = np.nan
        O[:] = np.nan
        shape[:] = np.nan
        scale = np.full(G, np.nan) if per_group else np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -1
    else:
        sigma = _sigma_from_orientation(O, shape, scale, p, G, per_group)
        niterin, WARNING = _iteration_status(niterin, itmax, warn)
        ret = 2

    info = {"iteration": niterin, "error": errin}
    variance = {
        "modelName": model,
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": model,
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "info": info,
        "WARNING": WARNING,
        "returnCode": ret,
    }


def mstepEVE(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
    control: dict | None = None,
) -> dict[str, Any]:
    """M-step for the EVE model: equal volume and orientation, variable shape."""
    return _mstep_orientation_model("EVE", data, z, prior, warn, control)


def mstepVVE(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
    control: dict | None = None,
) -> dict[str, Any]:
    """M-step for the VVE model: equal orientation, variable volume and shape."""
    return _mstep_orientation_model("VVE", data, z, prior, warn, control)
