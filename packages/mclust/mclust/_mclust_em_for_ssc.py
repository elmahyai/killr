"""Private EM steps (mstep, estep, cdens, dens) for MclustSSC via mclust Fortran."""

from __future__ import annotations

import ctypes
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from mclust._mclust_mutils import logsumexp_rows

_DOUBLE_XMAX = float(np.finfo(float).tiny)  # placeholder replaced below
_MACHINE_DOUBLE_XMAX = float(1.79769313486232e308)


def _f64(a: np.ndarray) -> np.ndarray:
    return np.asfortranarray(np.asarray(a, dtype=float))


def _owned(a) -> np.ndarray:
    """Fortran-ordered float64 copy, so a routine that writes its arguments cannot touch the caller's array."""
    return np.array(np.atleast_1d(np.asarray(a, dtype=np.float64)), dtype=np.float64, order="F", copy=True)


def _i32(x: int) -> ctypes.c_int:
    return ctypes.c_int(int(x))


def _iref(x: int) -> ctypes._SimpleCData:
    return ctypes.byref(_i32(x))


def _lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is None:
        so = Path(__file__).resolve().parents[3] / "crates" / "mclustbootstraplrt" / "libmclust_fortran.so"
        if not so.is_file():
            raise FileNotFoundError(f"mclust Fortran library missing: {so}")
        _LIB = ctypes.CDLL(str(so))
    return _LIB


_LIB: ctypes.CDLL | None = None


def _logsumexp_fortran(x: np.ndarray, v: np.ndarray | None = None) -> np.ndarray:
    x = np.atleast_2d(np.asarray(x, dtype=float))
    n, k = x.shape
    v = np.zeros(k, dtype=float) if v is None else np.asarray(v, dtype=float).ravel()
    lse = np.zeros(n, dtype=float)
    _lib().logsumexp_(
        x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(k),
        v.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        lse.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    return lse


def map_z(z: np.ndarray, *, warn: bool = False) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    n, k = z.shape
    cl = np.empty(n, dtype=int)
    for i in range(n):
        row = z[i, :]
        cl[i] = int(np.argmax(row)) + 1
    if warn:
        used = set(cl.tolist())
        missing = [j + 1 for j in range(k) if (j + 1) not in used]
        if missing:
            import warnings

            warnings.warn(f"no assignment to {','.join(map(str, missing))}", stacklevel=3)
    return cl


def _check_z(data: np.ndarray, z: np.ndarray) -> tuple[int, int, int]:
    data = _f64(data)
    z = _f64(z)
    n, p = data.shape
    if z.shape[0] != n:
        raise ValueError("row dimension of z should equal data length")
    g = z.shape[1]
    if np.any(np.isnan(z)) or np.any(z < 0) or np.any(z > 1):
        raise ValueError("improper specification of z")
    return n, p, g


def _build_sigma_diag(p: int, g: int, sigmasq) -> tuple[np.ndarray, np.ndarray]:
    if np.isscalar(sigmasq):
        sigma = np.zeros((p, p, g), dtype=float)
        sigma_diag = np.diag(np.full(p, float(sigmasq)))
        for k in range(g):
            sigma[:, :, k] = sigma_diag
        return sigma, sigma_diag
    sigmasq = np.asarray(sigmasq, dtype=float).ravel()
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = np.diag(np.full(p, sigmasq[k]))
    return sigma, np.diag(np.full(p, sigmasq[0]))


def _mstep_eii(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    sigmasq = np.zeros(1, dtype=float)
    pro = np.zeros(g, dtype=float)
    if prior is not None:
        raise NotImplementedError("prior not supported in MclustSSC path")
    _lib().mseii_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        sigmasq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sq = float(sigmasq[0])
    sigma, sigma0 = _build_sigma_diag(p, g, sq)
    variance = {"modelName": "EII", "d": p, "G": g, "sigma": sigma, "Sigma": sigma0, "sigmasq": sq, "scale": sq}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "EII", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_vii(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    sigmasq = np.zeros(g, dtype=float)
    pro = np.zeros(g, dtype=float)
    if prior is not None:
        raise NotImplementedError("prior not supported in MclustSSC path")
    _lib().msvii_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        sigmasq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = np.diag(np.full(p, sigmasq[k]))
    variance = {
        "modelName": "VII",
        "d": p,
        "G": g,
        "sigma": sigma,
        "Sigma": sigma[:, :, 0],
        "sigmasq": sigmasq.copy(),
        "scale": sigmasq.copy(),
    }
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "VII", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_eei(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    scale = np.zeros(1, dtype=float)
    shape = np.zeros(p, dtype=float)
    pro = np.zeros(g, dtype=float)
    _lib().mseei_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sc = float(scale[0])
    sh = shape.copy()
    sigma = np.zeros((p, p, g), dtype=float)
    sigma0 = np.diag(sc * sh)
    for k in range(g):
        sigma[:, :, k] = sigma0
    variance = {"modelName": "EEI", "d": p, "G": g, "sigma": sigma, "Sigma": sigma0, "scale": sc, "shape": sh}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "EEI", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_vei(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    scale = np.zeros(g, dtype=float)
    shape = np.zeros(p, dtype=float)
    pro = np.zeros(g, dtype=float)
    _lib().msvei_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = np.diag(scale[k] * shape)
    variance = {"modelName": "VEI", "d": p, "G": g, "sigma": sigma, "Sigma": sigma[:, :, 0], "scale": scale.copy(), "shape": shape.copy()}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "VEI", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_evi(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    scale = np.zeros(1, dtype=float)
    shape = np.zeros(p * g, dtype=float, order="F")
    pro = np.zeros(g, dtype=float)
    _lib().msevi_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sh = shape.reshape(p, g, order="F")
    sc = float(scale[0])
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = np.diag(sc * sh[:, k])
    variance = {"modelName": "EVI", "d": p, "G": g, "sigma": sigma, "Sigma": sigma[:, :, 0], "scale": sc, "shape": sh}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "EVI", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_vvi(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    scale = np.zeros(g, dtype=float)
    shape = np.zeros(p * g, dtype=float, order="F")
    pro = np.zeros(g, dtype=float)
    _lib().msvvi_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    sc = scale.copy()
    sh = shape.reshape(p, g, order="F")
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = np.diag(sc[k] * sh[:, k])
    variance = {"modelName": "VVI", "d": p, "G": g, "sigma": sigma, "Sigma": sigma[:, :, 0], "scale": sc, "shape": sh}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "VVI", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_eee(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    u = np.zeros(p * p, dtype=float, order="F")
    pro = np.zeros(g, dtype=float)
    work = np.zeros(p, dtype=float)
    _lib().mseee_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        work.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        u.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    chol = u.reshape(p, p, order="F")
    sigma_arr = np.zeros((p, p, g), dtype=float, order="F")
    sigma0 = np.zeros((p, p), dtype=float, order="F")
    info = ctypes.c_int(0)
    _lib().uncholf_(ctypes.byref(ctypes.c_int(1)), sigma0.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), _iref(p), _iref(p), ctypes.byref(info))
    for k in range(g):
        sigma_arr[:, :, k] = sigma0
    variance = {"modelName": "EEE", "d": p, "G": g, "sigma": sigma_arr, "Sigma": sigma0, "cholSigma": chol}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "EEE", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


def _mstep_vee(data: np.ndarray, z: np.ndarray, *, prior=None, warn: bool = False) -> dict[str, Any]:
    n, p, g = _check_z(data, z)
    data = _f64(data)
    z = _f64(z)
    mu = np.zeros(p * g, dtype=float, order="F")
    scale = np.zeros(g, dtype=float)
    shape = np.zeros(p, dtype=float)
    orient = np.zeros(p * p, dtype=float, order="F")
    pro = np.zeros(g, dtype=float)
    _lib().msvee_(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        orient.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    mu_m = mu.reshape(p, g, order="F")
    o = orient.reshape(p, p, order="F")
    sigma = np.zeros((p, p, g), dtype=float)
    for k in range(g):
        sigma[:, :, k] = scale[k] * (o @ np.diag(shape) @ o.T)
    variance = {"modelName": "VEE", "d": p, "G": g, "sigma": sigma, "Sigma": sigma[:, :, 0], "scale": scale.copy(), "shape": shape.copy(), "orientation": o}
    parameters = {"pro": pro.copy(), "mean": mu_m, "variance": variance}
    return {"modelName": "VEE", "prior": prior, "n": n, "d": p, "G": g, "z": z, "parameters": parameters}


# --- E-step helpers for es* from mclust.f ---

def _estep_es(
    model_name: str,
    fortran_name: str,
    data: np.ndarray,
    parameters: dict[str, Any],
    *,
    warn: bool = False,
    cdens_only: bool = False,
) -> tuple[np.ndarray, float]:
    # Every array handed to the Fortran routine is a copy: eseei, esevi, esvei,
    # esvvi and esvii rescale their scale/shape/sigsq arguments in place.
    data = _owned(data)
    n, p = data.shape
    mu = _owned(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    k = g
    vinv = np.array([-1.0], dtype=np.float64)
    loglik = np.zeros(1, dtype=np.float64)
    z = np.zeros((n, k), dtype=np.float64, order="F")
    var = parameters["variance"]
    fn = getattr(_lib(), f"{fortran_name}_")
    pro_arg = np.array([-1.0], dtype=np.float64) if cdens_only else _owned(pro)
    if model_name == "EII":
        sigmasq = np.array([float(var["sigmasq"])], dtype=np.float64)
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            sigmasq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _iref(n),
            _iref(p),
            _iref(g),
            vinv.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name == "VII":
        sigmasq = _owned(var["sigmasq"])
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            sigmasq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _iref(n),
            _iref(p),
            _iref(g),
            vinv.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name in ("EEI", "VEI"):
        scale = _owned(var["scale"])
        shape = _owned(var["shape"])
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _iref(n),
            _iref(p),
            _iref(g),
            vinv.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name in ("EVI", "VVI"):
        scale = _owned(var["scale"])
        shape = _owned(var["shape"])
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _iref(n),
            _iref(p),
            _iref(g),
            vinv.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    else:
        raise NotImplementedError(model_name)
    z_m = np.asarray(z, dtype=float)
    ll = float(loglik[0])
    if ll > _MACHINE_DOUBLE_XMAX * 1e-6:
        z_m[:] = np.nan
        ll = float("nan")
    return z_m, ll


def _estep_eee(data: np.ndarray, parameters: dict[str, Any], *, warn: bool = False) -> dict[str, Any]:
    data = _f64(data)
    n, p = data.shape
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    mu = _f64(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    chol = _f64(np.asarray(parameters["variance"]["cholSigma"], dtype=float))
    flag = ctypes.c_int(1)
    vinv = ctypes.c_double(-1.0)
    work = np.zeros(p, dtype=float, order="F")
    loglik = np.zeros(1, dtype=float, order="F")
    z = np.zeros(n * g, dtype=float, order="F")
    _lib().eseee_(
        ctypes.byref(flag),
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        chol.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        ctypes.byref(vinv),
        work.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    ll = float(loglik[0])
    if int(work[0]) != 0 or ll > _MACHINE_DOUBLE_XMAX * 1e-6:
        ll = float("nan")
        z_m = np.full((n, g), np.nan)
    else:
        z_m = z.reshape(n, g, order="F")
    return {
        "modelName": "EEE",
        "n": n,
        "d": p,
        "G": g,
        "z": z_m,
        "parameters": parameters,
        "loglik": ll,
    }


def _cdens_eee(data: np.ndarray, parameters: dict[str, Any], *, logarithm: bool = False, warn: bool = False) -> np.ndarray:
    data = _f64(data)
    n, p = data.shape
    mu = _f64(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    chol = _f64(np.asarray(parameters["variance"]["cholSigma"], dtype=float))
    pro = np.array([-1.0] * g, dtype=float)
    flag = ctypes.c_int(1)
    vinv = ctypes.c_double(-1.0)
    work = np.zeros(p, dtype=float, order="F")
    loglik = np.zeros(1, dtype=float, order="F")
    z = np.zeros(n * g, dtype=float, order="F")
    _lib().eseee_(
        ctypes.byref(flag),
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        chol.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _iref(n),
        _iref(p),
        _iref(g),
        ctypes.byref(vinv),
        work.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    z_m = z.reshape(n, g, order="F")
    if int(work[0]) != 0:
        z_m[:] = np.nan
    elif not logarithm:
        z_m = np.exp(z_m)
    return z_m


MSTEP = {
    "EII": _mstep_eii,
    "VII": _mstep_vii,
    "EEE": _mstep_eee,
}

ESTEP_FN = {
    "EII": ("eseii", _estep_es),
    "VII": ("esvii", _estep_es),
    "EEE": (None, _estep_eee),
    "VEE": (None, None),
}


def em_mstep(
    data: np.ndarray,
    z: np.ndarray,
    *,
    model_name: str,
    prior=None,
    control=None,
    warn: bool = False,
) -> dict[str, Any]:
    name = model_name
    if name not in MSTEP:
        raise NotImplementedError(f"mstep for model {name}")
    return MSTEP[name](data, z, prior=prior, warn=warn)


def em_estep(
    data: np.ndarray,
    fit_m: dict[str, Any],
    *,
    control=None,
    warn: bool = False,
) -> dict[str, Any]:
    model_name = fit_m["modelName"]
    parameters = fit_m["parameters"]
    if model_name == "EEE":
        out = _estep_eee(data, parameters, warn=warn)
        return {**fit_m, **out}
    spec = ESTEP_FN.get(model_name)
    if spec is None or spec[0] is None:
        raise NotImplementedError(f"estep for model {model_name}")
    fn_name, _ = spec
    z, loglik = _estep_es(model_name, fn_name, data, parameters, warn=warn, cdens_only=False)
    n, p = data.shape
    g = fit_m["G"]
    return {
        **fit_m,
        "z": z,
        "loglik": loglik,
        "n": n,
        "d": p,
        "G": g,
    }


def em_cdens(
    data: np.ndarray,
    fit_m: dict[str, Any],
    *,
    logarithm: bool = False,
    warn: bool = False,
) -> np.ndarray:
    model_name = fit_m["modelName"]
    parameters = fit_m["parameters"]
    if model_name == "EEE":
        return _cdens_eee(data, parameters, logarithm=logarithm, warn=warn)
    spec = ESTEP_FN.get(model_name)
    if spec is None or spec[0] is None:
        raise NotImplementedError(f"cdens for model {model_name}")
    fn_name, _ = spec
    z, _ = _estep_es(model_name, fn_name, data, parameters, warn=warn, cdens_only=True)
    if not logarithm:
        z = np.exp(z)
    return z


def em_dens(
    data: np.ndarray,
    fit_m: dict[str, Any],
    *,
    logarithm: bool = False,
    warn: bool = False,
) -> np.ndarray:
    log_cden = em_cdens(data, fit_m, logarithm=True, warn=warn)
    pro = np.asarray(fit_m["parameters"]["pro"], dtype=float)
    pro = pro / pro.sum()
    proz = pro == 0
    if np.any(proz):
        pro = pro[~proz]
        log_cden = log_cden[:, ~proz]
    logden = _logsumexp_fortran(log_cden, np.log(pro))
    return logden if logarithm else np.exp(logden)
