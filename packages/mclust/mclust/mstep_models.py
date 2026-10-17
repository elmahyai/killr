"""M-step fits for the mclust one-dimensional and diagonal-volume models.

Translated from mclust 6.1.3 R/mclust.R: mstepE, mstepV, mstepEII, mstepEEI,
and mstepEVI. The arithmetic runs in the Fortran kernels from crates/mclust,
imported as the ``mclust_kernels`` module (ms1e, ms1v, mseii, mseei, msevi and
their prior variants).

The R ``prior`` argument is a dict whose ``functionName`` entry is a callable,
with the other entries passed to it as keyword arguments, as ``do.call`` does.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

import mclust_kernels as _k

from mclust.mclust_options import mclust_options

__all__ = ["mstepE", "mstepV", "mstepEII", "mstepEEI", "mstepEVI"]

# signif(.Machine$double.xmax, 6)
_MAX = 1.79769e308


def _warn_flag(warn: Any) -> bool:
    if warn is None:
        warn = mclust_options("warn")
    return bool(warn)


def _emit(warn: bool, message: str) -> None:
    if warn:
        warnings.warn(message, stacklevel=3)


def _data_one_d(data: Any) -> np.ndarray:
    x = np.atleast_1d(np.asarray(data, dtype=float))
    if x.ndim == 2 and x.shape[1] == 1:
        x = x[:, 0]
    if x.ndim != 1:
        raise ValueError("data must be one-dimensional")
    return x


def _data_matrix(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim != 2 or x.shape[1] == 1:
        raise ValueError("data should be a matrix")
    return x


def _z_matrix(z: Any, n: int) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    if z.ndim != 2 or z.shape[0] != n:
        raise ValueError("row dimension of z should equal data length")
    return z


def _check_z(z: np.ndarray) -> None:
    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")


def _kernel(name: str, *args: Any) -> list:
    """Call one mclust_kernels binding, which takes a single tuple."""
    return getattr(_k, name)(tuple(args))


def _f(a: Any) -> list[float]:
    """as.double(): flatten column-major to a list of floats."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def _scalar(v: Any) -> float:
    a = np.asarray(v, dtype=float).ravel(order="F")
    if a.size != 1:
        raise ValueError("prior parameter must be a scalar for this model")
    return float(a[0])


def _prior_params(prior: dict, data: np.ndarray, G: int, model_name: str) -> dict:
    extra = {k: v for k, v in prior.items() if k != "functionName"}
    return prior["functionName"](data=data, G=G, modelName=model_name, **extra)


def _result(model, prior, n, d, G, z, parameters, ret, warning):
    return {
        "modelName": model,
        "prior": prior,
        "n": n,
        "d": d,
        "G": G,
        "z": z,
        "parameters": parameters,
        "WARNING": warning,
        "returnCode": ret,
    }


def mstepE(data, z, prior=None, warn=None, **kwargs):
    """M-step for the one-dimensional equal-variance model E."""
    warn = _warn_flag(warn)
    x = _data_one_d(data)
    n = x.size
    z = _z_matrix(z, n)
    G = z.shape[1]
    if np.all(np.isnan(z)):
        msg = "z is missing"
        _emit(warn, msg)
        variance = {"modelName": "E", "d": 1, "G": G, "sigmasq": np.nan}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full(G, np.nan),
            "variance": variance,
        }
        return _result("E", prior, n, 1, G, z, parameters, 9, msg)
    _check_z(z)
    zf = _f(z)
    if prior is None:
        out = _kernel("ms1e", _f(x), zf, n, G, [0.0] * G, 0.0, [0.0] * G)
        mu, sigsq, pro = out[4], out[5], out[6]
    else:
        pp = _prior_params(prior, x, G, "E")
        out = _kernel("ms1ep", 
            _f(x), zf, n, G,
            _scalar(pp["shrinkage"]), _scalar(pp["mean"]),
            _scalar(pp["scale"]), _scalar(pp["dof"]),
            [0.0] * G, 0.0, [0.0] * G,
        )
        mu, sigsq, pro = out[8], out[9], out[10]
    mu = np.asarray(mu, dtype=float)
    pro = np.asarray(pro, dtype=float)
    sigsq = float(sigsq)
    msg, ret = None, 0
    if sigsq > _MAX:
        msg = "cannot compute M-step"
        _emit(warn, msg)
        pro[:] = np.nan
        mu[:] = np.nan
        sigsq = np.nan
        ret = -1
    variance = {"modelName": "E", "d": 1, "G": G, "sigmasq": sigsq}
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return _result("E", prior, n, 1, G, z, parameters, ret, msg)


def mstepV(data, z, prior=None, warn=None, **kwargs):
    """M-step for the one-dimensional unequal-variance model V."""
    warn = _warn_flag(warn)
    x = _data_one_d(data)
    n = x.size
    z = _z_matrix(z, n)
    G = z.shape[1]
    if np.all(np.isnan(z)):
        msg = "z is missing"
        _emit(warn, msg)
        variance = {"modelName": "V", "d": 1, "G": G, "sigmasq": np.full(G, np.nan)}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full(G, np.nan),
            "variance": variance,
        }
        return _result("V", prior, n, 1, G, z, parameters, 9, msg)
    _check_z(z)
    zf = _f(z)
    if prior is None:
        out = _kernel("ms1v", _f(x), zf, n, G, [0.0] * G, [0.0] * G, [0.0] * G)
        mu, sigsq, pro = out[4], out[5], out[6]
    else:
        pp = _prior_params(prior, x, G, "V")
        out = _kernel("ms1vp", 
            _f(x), zf, n, G,
            _scalar(pp["shrinkage"]), _scalar(pp["mean"]),
            _scalar(pp["scale"]), _scalar(pp["dof"]),
            [0.0] * G, [0.0] * G, [0.0] * G,
        )
        mu, sigsq, pro = out[8], out[9], out[10]
    mu = np.asarray(mu, dtype=float)
    sigsq = np.asarray(sigsq, dtype=float)
    pro = np.asarray(pro, dtype=float)
    msg, ret = None, 0
    if np.any(sigsq > _MAX):
        msg = "cannot compute M-step"
        _emit(warn, msg)
        mu[:] = np.nan
        pro[:] = np.nan
        sigsq[:] = np.nan
        z = np.full_like(z, np.nan)
        ret = -1
    variance = {"modelName": "V", "d": 1, "G": G, "sigmasq": sigsq, "scale": sigsq}
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return _result("V", prior, n, 1, G, z, parameters, ret, msg)


def mstepEII(data, z, prior=None, warn=None, **kwargs):
    """M-step for the spherical equal-volume model EII."""
    warn = _warn_flag(warn)
    x = _data_matrix(data)
    n, p = x.shape
    z = _z_matrix(z, n)
    G = z.shape[1]
    if np.all(np.isnan(z)):
        msg = "z is missing"
        _emit(warn, msg)
        variance = {"modelName": "EII", "d": p, "G": G, "sigmasq": np.nan}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full((p, G), np.nan),
            "variance": variance,
        }
        return _result("EII", prior, n, p, G, z, parameters, 9, msg)
    _check_z(z)
    zf = _f(z)
    if prior is None:
        out = _kernel("mseii", _f(x), zf, n, p, G, [0.0] * (p * G), 0.0, [0.0] * G)
        mu, sigsq, pro = out[5], out[6], out[7]
    else:
        pp = _prior_params(prior, x, G, "EII")
        out = _kernel("mseiip", 
            _f(x), zf, n, p, G,
            _scalar(pp["shrinkage"]), _f(pp["mean"]),
            _scalar(pp["scale"]), _scalar(pp["dof"]),
            [0.0] * (p * G), 0.0, [0.0] * G,
        )
        mu, sigsq, pro = out[9], out[10], out[11]
    mu = np.asarray(mu, dtype=float).reshape((p, G), order="F")
    pro = np.asarray(pro, dtype=float)
    sigsq = float(sigsq)
    Sigma = np.eye(p) * sigsq
    sigma = np.zeros((p, p, G))
    for k in range(G):
        sigma[:, :, k] = Sigma
    msg, ret = None, 0
    if sigsq > _MAX:
        msg = "cannot compute M-step"
        _emit(warn, msg)
        ret = -1
    variance = {
        "modelName": "EII", "d": p, "G": G, "sigma": sigma, "Sigma": Sigma,
        "sigmasq": sigsq, "scale": sigsq,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return _result("EII", prior, n, p, G, z, parameters, ret, msg)


def mstepEEI(data, z, prior=None, warn=None, **kwargs):
    """M-step for the diagonal equal-volume model EEI."""
    warn = _warn_flag(warn)
    x = _data_matrix(data)
    n, p = x.shape
    z = _z_matrix(z, n)
    G = z.shape[1]
    if np.all(np.isnan(z)):
        msg = "z is missing"
        _emit(warn, msg)
        variance = {"modelName": "EEI", "d": p, "G": G, "scale": np.nan, "shape": np.full(p, np.nan)}
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full((p, G), np.nan),
            "variance": variance,
        }
        return _result("EEI", prior, n, p, G, z, parameters, 9, msg)
    _check_z(z)
    zf = _f(z)
    if prior is None:
        out = _kernel("mseei", _f(x), zf, n, p, G, [0.0] * (p * G), 0.0, [0.0] * p, [0.0] * G)
        mu, scale, shape, pro = out[5], out[6], out[7], out[8]
    else:
        pp = _prior_params(prior, x, G, "EEI")
        out = _kernel("mseeip", 
            _f(x), zf, n, p, G,
            _scalar(pp["shrinkage"]), _f(pp["mean"]),
            _scalar(pp["scale"]), _scalar(pp["dof"]),
            [0.0] * (p * G), 0.0, [0.0] * p, [0.0] * G,
        )
        mu, scale, shape, pro = out[9], out[10], out[11], out[12]
    mu = np.asarray(mu, dtype=float).reshape((p, G), order="F")
    scale = float(scale)
    shape = np.asarray(shape, dtype=float)
    pro = np.asarray(pro, dtype=float)
    msg, ret = None, 0
    vals = np.concatenate([[scale], shape])
    if np.any(vals > _MAX) or np.any(vals == 0):
        msg = "cannot compute M-step"
        _emit(warn, msg)
        mu[:] = np.nan
        pro[:] = np.nan
        scale = np.nan
        shape[:] = np.nan
        sigma = np.full((p, p, G), np.nan)
        Sigma = np.full((p, p, G), np.nan)
        ret = -1
    else:
        Sigma = np.diag(scale * shape)
        sigma = np.zeros((p, p, G))
        for k in range(G):
            sigma[:, :, k] = Sigma
    variance = {
        "modelName": "EEI", "d": p, "G": G, "sigma": sigma, "Sigma": Sigma,
        "scale": scale, "shape": shape,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return _result("EEI", prior, n, p, G, z, parameters, ret, msg)


def mstepEVI(data, z, prior=None, warn=None, **kwargs):
    """M-step for the diagonal equal-shape model EVI."""
    warn = _warn_flag(warn)
    x = _data_matrix(data)
    n, p = x.shape
    z = _z_matrix(z, n)
    G = z.shape[1]
    if np.all(np.isnan(z)):
        msg = "z is missing"
        _emit(warn, msg)
        variance = {
            "modelName": "EVI", "d": p, "G": G,
            "scale": np.nan, "shape": np.full((p, G), np.nan),
        }
        parameters = {
            "pro": np.full(G, np.nan),
            "mean": np.full((p, G), np.nan),
            "variance": variance,
        }
        return _result("EVI", prior, n, p, G, z, parameters, 9, msg)
    _check_z(z)
    zf = _f(z)
    if prior is None:
        out = _kernel("msevi", _f(x), zf, n, p, G, [0.0] * (p * G), 0.0, [0.0] * (p * G), [0.0] * G)
        mu, scale, shape, pro = out[5], out[6], out[7], out[8]
    else:
        pp = _prior_params(prior, x, G, "EVI")
        out = _kernel("msevip", 
            _f(x), zf, n, p, G,
            _scalar(pp["shrinkage"]), _f(pp["mean"]),
            _scalar(pp["scale"]), _scalar(pp["dof"]),
            [0.0] * (p * G), 0.0, [0.0] * (p * G), [0.0] * G,
        )
        mu, scale, shape, pro = out[9], out[10], out[11], out[12]
    mu = np.asarray(mu, dtype=float).reshape((p, G), order="F")
    scale = float(scale)
    shape = np.asarray(shape, dtype=float).reshape((p, G), order="F")
    pro = np.asarray(pro, dtype=float)
    msg, ret = None, 0
    vals = np.concatenate([[scale], shape.ravel(order="F")])
    if np.any(vals > _MAX) or np.any(vals == 0):
        msg = "cannot compute M-step"
        _emit(warn, msg)
        mu[:] = np.nan
        pro[:] = np.nan
        scale = np.nan
        shape[:] = np.nan
        sigma = np.full((p, p, G), np.nan)
        ret = -1
    else:
        sigma = np.zeros((p, p, G))
        for k in range(G):
            sigma[:, :, k] = np.diag(scale * shape[:, k])
    variance = {
        "modelName": "EVI", "d": p, "G": G, "sigma": sigma,
        "scale": scale, "shape": shape,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance}
    return _result("EVI", prior, n, p, G, z, parameters, ret, msg)
