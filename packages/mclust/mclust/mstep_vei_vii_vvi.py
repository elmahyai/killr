"""M-step for the VEI, VII, and VVI models of mclust 6.1.3 (mstep.R).

Each public function mirrors the R function of the same name: the argument
checks, the all-missing ``z`` return, the prior step, the status codes, and
the fields of the returned list. The numerical work is done by the ``msvei``,
``msveip``, ``msvii``, ``msviip``, ``msvvi``, and ``msvvip`` kernels in the
``mclust_kernels`` crate, which take one tuple of arguments in the order the
R ``.Fortran`` calls use.

R stores ``info`` and ``returnCode`` as attributes of the result for VEI and
VVI and VII. Here they are keys of the returned dict. VII has no ``info``, and
VVI has no ``info`` and no ``control``, as in R.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._me_common import (
    XMAX6,
    check_z,
    default_control,
    emit,
    farr,
    fflat,
    kernels,
    nan_like,
    prior_params,
    resolve_warn,
    scalar,
    z_matrix,
)

__all__ = ["mstep_vei", "mstep_vii", "mstep_vvi"]


def _data_matrix(data: Any, message: str) -> np.ndarray:
    """R: ``oneD || length(dimdat) != 2`` stops, so one column is an error too."""
    x = np.asarray(data, dtype=float)
    if x.ndim != 2 or x.shape[1] == 1:
        raise ValueError(message)
    return x


def _control_pick(values: Any) -> float:
    """R: ``if (length(x) == 1) x else x[2]``, read before any padding."""
    raw = np.ravel(np.asarray(values, dtype=float))
    return float(raw[0]) if raw.size == 1 else float(raw[1])


def _zeros(m: int) -> list[float]:
    return [0.0] * m


def mstep_vei(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
    control: Any = None,
) -> dict[str, Any]:
    """M-step for the VEI model (equal orientation, variable volume, diagonal shape)."""
    warn = resolve_warn(warn)
    x = _data_matrix(data, "data should be a matrix or a vector")
    n, p = x.shape
    zz = z_matrix(z, n, "row dimension of z should equal data length")
    G = zz.shape[1]
    if np.all(np.isnan(zz)):
        WARNING = "z is missing"
        emit(warn, WARNING)
        variance = {"modelName": "VEI", "d": p, "G": G, "scale": nan_like(G), "shape": nan_like(p)}
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance}
        return {
            "modelName": "VEI",
            "prior": prior,
            "n": n,
            "d": p,
            "G": G,
            "z": zz,
            "parameters": parameters,
            "control": control,
            "loglik": float("nan"),
            "WARNING": WARNING,
            "returnCode": 9,
        }
    check_z(zz)
    control = default_control(control)
    itmax = int(_control_pick(control["itmax"]))
    tol = _control_pick(control["tol"])

    k = kernels()
    x_flat = fflat(x)
    z_flat = fflat(zz)
    if prior is None:
        out = k.msvei(
            (
                x_flat,
                z_flat,
                n,
                p,
                G,
                itmax,
                tol,
                _zeros(p * G),
                _zeros(G),
                _zeros(p),
                _zeros(G),
                _zeros(G),
                _zeros(p),
                _zeros(p * G),
            )
        )
        inner, inerr = int(out[5]), float(out[6])
        mu_flat, scale, shape, pro = out[7], out[8], out[9], out[10]
    else:
        pp = prior_params(prior, x, G, "VEI")
        out = k.msveip(
            (
                x_flat,
                z_flat,
                n,
                p,
                G,
                float(scalar(pp["shrinkage"])),
                fflat(pp["mean"]),
                float(scalar(pp["scale"])),
                float(scalar(pp["dof"])),
                itmax,
                tol,
                _zeros(p * G),
                _zeros(G),
                _zeros(p),
                _zeros(G),
                _zeros(G),
                _zeros(p),
                _zeros(p * G),
            )
        )
        inner, inerr = int(out[9]), float(out[10])
        mu_flat, scale, shape, pro = out[11], out[12], out[13], out[14]

    mu = farr(mu_flat, (p, G))
    scale = np.asarray(scale, dtype=float)
    shape = np.asarray(shape, dtype=float)
    pro = np.asarray(pro, dtype=float)
    WARNING = None
    both = np.concatenate([scale, shape])
    if np.any(both > XMAX6) or np.any(both == 0):
        WARNING = "cannot compute M-step"
        emit(warn, WARNING)
        # R: mu[] <- pro[] <- shape <- scale[] <- NA. Assigning to `shape` makes it a scalar NA.
        mu[...] = np.nan
        pro = nan_like(G)
        shape = np.float64(np.nan)
        scale = nan_like(G)
        sigma = nan_like((p, p, G))
        ret = -1
    else:
        ret = 0
        sigma = np.zeros((p, p, G))
        for g in range(G):
            sigma[:, :, g] = np.diag(scale[g] * shape)
        if inner >= itmax:
            WARNING = "inner iteration limit reached"
            emit(warn, WARNING)
            inner = -inner

    info = {"iterations": inner, "error": inerr}
    variance = {
        "modelName": "VEI",
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": "VEI",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": zz,
        "parameters": parameters,
        "control": control,
        "info": info,
        "WARNING": WARNING,
        "returnCode": ret,
    }


def mstep_vii(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
) -> dict[str, Any]:
    """M-step for the VII model (equal spherical covariance, variable volume)."""
    warn = resolve_warn(warn)
    x = _data_matrix(data, "data should be a matrix")
    n, p = x.shape
    zz = z_matrix(z, n, "row dimension of z should equal number of observations")
    G = zz.shape[1]
    if np.all(np.isnan(zz)):
        WARNING = "z is missing"
        emit(warn, WARNING)
        variance = {"modelName": "VII", "d": p, "G": G, "sigmasq": nan_like(G)}
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance}
        return {
            "modelName": "VII",
            "prior": prior,
            "n": n,
            "d": p,
            "G": G,
            "z": zz,
            "parameters": parameters,
            "WARNING": WARNING,
            "returnCode": 9,
        }
    check_z(zz)

    k = kernels()
    x_flat = fflat(x)
    z_flat = fflat(zz)
    if prior is None:
        out = k.msvii((x_flat, z_flat, n, p, G, _zeros(p * G), _zeros(G), _zeros(G)))
        mu_flat, sigmasq, pro = out[5], out[6], out[7]
    else:
        pp = prior_params(prior, x, G, "VII")
        out = k.msviip(
            (
                x_flat,
                z_flat,
                n,
                p,
                G,
                float(scalar(pp["shrinkage"])),
                fflat(pp["mean"]),
                float(scalar(pp["scale"])),
                float(scalar(pp["dof"])),
                _zeros(p * G),
                _zeros(G),
                _zeros(G),
            )
        )
        mu_flat, sigmasq, pro = out[9], out[10], out[11]

    mu = farr(mu_flat, (p, G))
    sigmasq = np.asarray(sigmasq, dtype=float)
    pro = np.asarray(pro, dtype=float)
    sigma = np.zeros((p, p, G))
    for g in range(G):
        sigma[:, :, g] = np.eye(p) * sigmasq[g]
    WARNING = None
    if np.any(sigmasq > XMAX6):
        WARNING = "cannot compute M-step"
        emit(warn, WARNING)
        ret = -1
    else:
        ret = 0
    variance = {
        "modelName": "VII",
        "d": p,
        "G": G,
        "sigma": sigma,
        "sigmasq": sigmasq,
        "scale": sigmasq,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": "VII",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": zz,
        "parameters": parameters,
        "WARNING": WARNING,
        "returnCode": ret,
    }


def mstep_vvi(
    data: Any,
    z: Any,
    prior: dict | None = None,
    warn: bool | None = None,
) -> dict[str, Any]:
    """M-step for the VVI model (diagonal covariance, variable volume and shape)."""
    warn = resolve_warn(warn)
    x = _data_matrix(data, "data should be a matrix or a vector")
    n, p = x.shape
    zz = z_matrix(z, n, "row dimension of z should equal data length")
    G = zz.shape[1]
    if np.all(np.isnan(zz)):
        WARNING = "z is missing"
        emit(warn, WARNING)
        # R's all-missing branch labels this result "VII", not "VVI". Kept as in R.
        variance = {"modelName": "VII", "d": p, "G": G, "sigmasq": nan_like(G)}
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance}
        return {
            "modelName": "VVI",
            "prior": prior,
            "n": n,
            "d": p,
            "G": G,
            "z": zz,
            "parameters": parameters,
            "WARNING": WARNING,
            "returnCode": 9,
        }
    check_z(zz)

    k = kernels()
    x_flat = fflat(x)
    z_flat = fflat(zz)
    if prior is None:
        out = k.msvvi(
            (x_flat, z_flat, n, p, G, _zeros(p * G), _zeros(G), _zeros(p * G), _zeros(G))
        )
        mu_flat, scale, shape, pro = out[5], out[6], out[7], out[8]
    else:
        pp = prior_params(prior, x, G, "VVI")
        out = k.msvvip(
            (
                x_flat,
                z_flat,
                n,
                p,
                G,
                float(scalar(pp["shrinkage"])),
                fflat(pp["mean"]),
                float(scalar(pp["scale"])),
                float(scalar(pp["dof"])),
                _zeros(p * G),
                _zeros(G),
                _zeros(p * G),
                _zeros(G),
            )
        )
        mu_flat, scale, shape, pro = out[9], out[10], out[11], out[12]

    mu = farr(mu_flat, (p, G))
    scale = np.asarray(scale, dtype=float)
    shape = farr(shape, (p, G))
    pro = np.asarray(pro, dtype=float)
    WARNING = None
    both = np.concatenate([scale, shape.ravel(order="F")])
    if np.any(both > XMAX6) or np.any(both == 0):
        WARNING = "cannot compute M-step"
        emit(warn, WARNING)
        # R: mu[] <- pro[] <- shape <- scale[] <- NA. Assigning to `shape` makes it a scalar NA.
        mu[...] = np.nan
        pro = nan_like(G)
        shape = np.float64(np.nan)
        scale = nan_like(G)
        sigma = nan_like((p, p, G))
        ret = -1
    else:
        sigma = np.zeros((p, p, G))
        for g in range(G):
            sigma[:, :, g] = np.diag(shape[:, g] * scale[g])
        ret = 0
    variance = {
        "modelName": "VVI",
        "d": p,
        "G": G,
        "sigma": sigma,
        "sigmasq": scale,
        "scale": scale,
        "shape": shape,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return {
        "modelName": "VVI",
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": zz,
        "parameters": parameters,
        "WARNING": WARNING,
        "returnCode": ret,
    }
