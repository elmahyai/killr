"""One-off generator for _mclust_em_for_ssc.py (run from repo root)."""

from pathlib import Path

OUT = Path(__file__).with_name("_mclust_em_for_ssc.py")

HEADER = '''\
"""Private EM steps (mstep, estep, cdens, dens) for MclustSSC via mclust Fortran."""

from __future__ import annotations

import ctypes
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from mclust._mclust_mutils import logsumexp_rows

try:
    from cvmclustda import uncholf
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "cvmclustda"))
    from cvmclustda import uncholf

_DOUBLE_XMAX = float(np.finfo(float).tiny)  # placeholder replaced below
_MACHINE_DOUBLE_XMAX = float(1.79769313486232e308)


def _f64(a: np.ndarray) -> np.ndarray:
    return np.asfortranarray(np.asarray(a, dtype=float))


def _i32(x: int) -> ctypes.c_int:
    return ctypes.c_int(int(x))


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
        _i32(n),
        _i32(k),
        v.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        lse.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    return lse


def _map_z(z: np.ndarray, *, warn: bool = False) -> np.ndarray:
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
        _i32(n),
        _i32(p),
        _i32(g),
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
        _i32(n),
        _i32(p),
        _i32(g),
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
        _i32(n),
        _i32(p),
        _i32(g),
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
        _i32(n),
        _i32(p),
        _i32(g),
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
        _i32(n),
        _i32(p),
        _i32(g),
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
        _i32(n),
        _i32(p),
        _i32(g),
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
    from mclust._mclust_eee import mstep_eee

    return mstep_eee(data, z, warn=warn)


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
        _i32(n),
        _i32(p),
        _i32(g),
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
    data = _f64(data)
    n, p = data.shape
    mu = _f64(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    k = g
    vinv = -1.0
    loglik = np.zeros(1, dtype=float)
    z = np.zeros(n * k, dtype=float, order="F")
    var = parameters["variance"]
    fn = getattr(_lib(), f"{fortran_name}_")
    if model_name == "EII":
        sigmasq = float(var["sigmasq"])
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_double(sigmasq),
            pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _i32(n),
            _i32(p),
            _i32(g),
            ctypes.c_double(vinv),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name == "VII":
        sigmasq = np.asarray(var["sigmasq"], dtype=float)
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            sigmasq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _i32(n),
            _i32(p),
            _i32(g),
            ctypes.c_double(vinv),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name in ("EEI", "VEI"):
        scale = np.asarray(var["scale"], dtype=float)
        shape = np.asarray(var["shape"], dtype=float)
        pro_arg = np.array([-1.0] * g, dtype=float) if cdens_only else pro
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _i32(n),
            _i32(p),
            _i32(g),
            ctypes.c_double(vinv),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    elif model_name in ("EVI", "VVI"):
        scale = np.asarray(var["scale"], dtype=float)
        shape = _f64(np.asarray(var["shape"], dtype=float))
        pro_arg = np.array([-1.0] * g, dtype=float) if cdens_only else pro
        fn(
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            scale.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            shape.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            pro_arg.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            _i32(n),
            _i32(p),
            _i32(g),
            ctypes.c_double(vinv),
            loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
    else:
        raise NotImplementedError(model_name)
    z_m = z.reshape(n, k, order="F")
    ll = float(loglik[0])
    if ll > _MACHINE_DOUBLE_XMAX * 1e-6:
        z_m[:] = np.nan
        ll = float("nan")
    return z_m, ll


def _estep_eee(data: np.ndarray, parameters: dict[str, Any], *, warn: bool = False) -> dict[str, Any]:
    from mclust._mclust_eee import estep_eee

    return estep_eee(data, parameters, warn=warn)


def _cdens_eee(data: np.ndarray, parameters: dict[str, Any], *, logarithm: bool = False, warn: bool = False) -> np.ndarray:
    from mclust._mclust_eee import cdens_eee

    return cdens_eee(data, parameters, logarithm=logarithm, warn=warn)


MSTEP = {
    "EII": _mstep_eii,
    "VII": _mstep_vii,
    "EEI": _mstep_eei,
    "VEI": _mstep_vei,
    "EVI": _mstep_evi,
    "VVI": _mstep_vvi,
    "EEE": _mstep_eee,
    "VEE": _mstep_vee,
}

ESTEP_FN = {
    "EII": ("eseii", _estep_es),
    "VII": ("esvii", _estep_es),
    "EEI": ("eseei", _estep_es),
    "VEI": ("esvei", _estep_es),
    "EVI": ("esevi", _estep_es),
    "VVI": ("esvvi", _estep_es),
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
'''

OUT.write_text(HEADER)
print("wrote", OUT)
