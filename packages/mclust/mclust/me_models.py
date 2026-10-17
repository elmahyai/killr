"""EM for the VEE, EVE, and VVE models, and the one-component X fits.

``meVEE``, ``meEVE``, and ``meVVE`` mirror the R functions of the same name in
``R/mclust2.R`` (mclust 6.1.3). Each one calls the Fortran EM subroutine
``mevee``, ``meeve``, or ``mevve`` from ``crates/mclust`` through the
``mclust_kernels`` extension, then rebuilds the parameters the way R does.

``meX``, ``meXII``, ``meXXI``, and ``meXXX`` are the single-component fits in
``R/mclust.R``. In R each one is the matching ``emX`` wrapper, which calls
``mvnX``, ``mvnXII``, ``mvnXXI``, or ``mvnXXX`` and does not iterate.

Arrays are column-major inside the kernels, as in R's ``.Fortran``. Logical
flags go to the kernels as 0 or 1.

A prior is not applied. R calls the prior's function first and then returns
a stub with ``returnCode`` -1. This module returns the same stub without
calling that function, and the stub carries only the scalar fields.
"""

from __future__ import annotations

import importlib.util
import math
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from mclust.em_control import em_control
from mclust.mclust_options import mclust_options
from mclust.mvn import mvnX, mvnXII, mvnXXI, mvnXXX
from mclust.utility_functions import hypvol

__all__ = ["meVEE", "meEVE", "meVVE", "meX", "meXII", "meXXI", "meXXX"]

# signif(.Machine$double.xmax, 6)
_XMAX_SIGNIF6 = float("1.79769e308")
# .Machine$double.xmax
_DBL_XMAX = sys.float_info.max

_KERNELS: Any = None

_ELLIPSOIDAL = {
    "VEE": {
        "kernel": "mevee",
        "fail": "LAPACK DSYEV or DPOTRI fails to converge",
        "input": "input error for LAPACK DPOTRF, DSYEV or DPOTRI",
    },
    "EVE": {
        "kernel": "meeve",
        "fail": "LAPACK DSYEV or DGESVD fails to converge",
        "input": "input error for LAPACK DSYEV or DGESVD",
    },
    "VVE": {
        "kernel": "mevve",
        "fail": "LAPACK DSYEV or DGESVD fails to converge",
        "input": "input error for LAPACK DSYEV or DGESVD",
    },
}


def _kernels() -> Any:
    """The ``mclust_kernels`` extension, from the installed module or the built library."""
    global _KERNELS
    if _KERNELS is None:
        try:
            import mclust_kernels as module
        except ImportError:
            so = (
                Path(__file__).resolve().parents[3]
                / "crates"
                / "mclust"
                / "target"
                / "release"
                / "libmclust_kernels.so"
            )
            if not so.is_file():
                raise FileNotFoundError(f"mclust_kernels library not found at {so}")
            spec = importlib.util.spec_from_file_location("mclust_kernels", so)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        _KERNELS = module
    return _KERNELS


def _first(value: Any) -> Any:
    """The single element of an R length-one vector."""
    if isinstance(value, (list, tuple, np.ndarray)):
        return value[0]
    return value


def _check_data(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim != 2 or x.shape[1] == 1:
        raise ValueError("data should in the form of a matrix")
    return x


def _check_z(z: Any, n: int) -> np.ndarray:
    zz = np.asarray(z, dtype=float)
    if zz.ndim == 1:
        zz = zz.reshape(-1, 1)
    if zz.ndim != 2 or zz.shape[0] != n:
        raise ValueError("data and z should have the same row dimension")
    return zz


def _svd_v(a: np.ndarray) -> np.ndarray:
    """``svd(a, nu = 0)$v``."""
    return np.linalg.svd(a, full_matrices=False)[2].T


def _z_missing(
    kind: str, n: int, p: int, G: int, z: np.ndarray, prior: Any, control: Any, warn: bool
) -> dict:
    message = "z is missing"
    if warn:
        warnings.warn(message)
    variance = {
        "modelName": kind,
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
        "modelName": kind,
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "loglik": float("nan"),
        "WARNING": message,
        "returnCode": 9,
    }


def _prior_unavailable(
    kind: str, n: int, p: int, G: int, z: np.ndarray, control: Any, warn: bool, lwork: int
) -> dict:
    message = f"{kind} model is not available with prior"
    if warn:
        warnings.warn(message)
    nan = float("nan")
    return {
        "n": n,
        "p": p,
        "G": G,
        "z": z,
        "eqpro": bool(control["equalPro"]),
        "lwork": lwork,
        "loglik": nan,
        "info": nan,
        "WARNING": message,
        "returnCode": -1,
    }


def _em_ellipsoidal(
    kind: str,
    data: Any,
    z: Any,
    prior: Any,
    control: Any,
    Vinv: float | None,
    warn: bool,
) -> dict:
    spec = _ELLIPSOIDAL[kind]
    if control is None:
        control = em_control()
    x = _check_data(data)
    n, p = x.shape
    z = _check_z(z, n)
    K = z.shape[1]
    if Vinv is not None:
        G = K - 1
        if Vinv <= 0:
            Vinv = hypvol(x, reciprocal=True)
    else:
        G = K

    if np.all(np.isnan(z)):
        return _z_missing(kind, n, p, G, z, prior, control, warn)
    if np.isnan(z).any() or (z < 0).any() or (z > 1).any():
        raise ValueError("improper specification of z")

    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)
    if prior is not None:
        return _prior_unavailable(kind, n, p, G, z, control, warn, lwork)

    eqpro = int(bool(control["equalPro"]))
    itmax = control["itmax"]
    tol = control["tol"]
    # R: itmax[1] and tol[1] are the outer loop, itmax[2] and tol[2] the inner loop.
    itmaxout = int(itmax[0])
    itmaxin = int(itmax[1])
    tolout = float(tol[0])
    tolin = float(tol[1])
    eps = float(_first(control["eps"]))

    eye = np.eye(p).ravel(order="F").tolist()
    if kind == "VEE":
        orient_in = [0.0] * (p * p)
        scale_in: Any = [0.0] * G
        shape_in = [0.0] * p
    elif kind == "EVE":
        orient_in = eye
        scale_in = 0.0
        shape_in = [1.0] * (p * G)
    else:
        orient_in = eye
        scale_in = [1.0] * G
        shape_in = [1.0] * (p * G)

    args = (
        x.ravel(order="F").tolist(),
        z.ravel(order="F").tolist(),
        n,
        p,
        G,
        K,
        [0.0] * (p * G),
        orient_in,
        [0.0] * (p * p * G),
        scale_in,
        shape_in,
        [0.0] * K,
        -1.0 if Vinv is None else float(Vinv),
        0.0,
        eqpro,
        itmaxin,
        tolin,
        itmaxout,
        tolout,
        eps,
        0,
        0.0,
        0,
        0.0,
        lwork,
        0,
    )
    out = getattr(_kernels(), spec["kernel"])(args)

    z_new = np.asarray(out[1], dtype=float).reshape(n, K, order="F")
    mu = np.asarray(out[6], dtype=float).reshape(p, G, order="F")
    orient_raw = np.asarray(out[7], dtype=float)
    scale = np.atleast_1d(np.asarray(out[9], dtype=float))
    shape_raw = np.asarray(out[10], dtype=float)
    pro = np.asarray(out[11], dtype=float)
    loglik = float(out[13])
    niterin = int(out[20])
    errin = float(out[21])
    niterout = int(out[22])
    errout = float(out[23])
    lapack = int(out[25])

    if kind == "VEE":
        shape = shape_raw
        shape_o = orient_raw.reshape(p, p, order="F")
        if np.isnan(shape_o).any():
            O = shape_o
        else:
            O = _svd_v(shape_o)
    else:
        shape = shape_raw.reshape(p, G, order="F")
        O = orient_raw.reshape(p, p, order="F").T

    if (
        not math.isfinite(loglik)
        or np.any(scale > _XMAX_SIGNIF6)
        or np.any(shape > _XMAX_SIGNIF6)
        or np.any(O > _XMAX_SIGNIF6)
        or np.isnan(scale).any()
        or np.isnan(shape).any()
        or np.isnan(O).any()
    ):
        loglik = _DBL_XMAX

    message = None
    sigma = np.full((p, p, G), np.nan)
    ret = 0
    if lapack != 0:
        message = spec["fail"] if lapack > 0 else spec["input"]
        if warn:
            warnings.warn(message)
        O = np.full_like(O, np.nan, dtype=float)
        shape = np.full_like(shape, np.nan, dtype=float)
        scale = np.full_like(scale, np.nan, dtype=float)
        mu = np.full_like(mu, np.nan, dtype=float)
        pro = np.full_like(pro, np.nan, dtype=float)
        z_new = np.full_like(z_new, np.nan, dtype=float)
        loglik = float("nan")
        ret = -9
    elif loglik > _XMAX_SIGNIF6:
        message = "singular covariance"
        if warn:
            warnings.warn(message)
        O = np.full_like(O, np.nan, dtype=float)
        shape = np.full_like(shape, np.nan, dtype=float)
        scale = np.full_like(scale, np.nan, dtype=float)
        mu = np.full_like(mu, np.nan, dtype=float)
        pro = np.full_like(pro, np.nan, dtype=float)
        z_new = np.full_like(z_new, np.nan, dtype=float)
        loglik = float("nan")
        ret = -1
    elif loglik < -_XMAX_SIGNIF6:
        if eqpro:
            message = "z column sum fell below threshold"
        else:
            message = "mixing proportion fell below threshold"
        if warn:
            warnings.warn(message)
        mu = np.full_like(mu, np.nan, dtype=float)
        pro = np.full_like(pro, np.nan, dtype=float)
        z_new = np.full_like(z_new, np.nan, dtype=float)
        loglik = float("nan")
        ret = -2 if eqpro else -3
    else:
        if kind == "VEE":
            sigma = shape_o[:, :, None] * scale[None, None, :]
        else:
            sigma = np.empty((p, p, G))
            for g in range(G):
                sg = scale[g] if scale.size > 1 else scale[0]
                sigma[:, :, g] = sg * O @ np.diag(shape[:, g]) @ O.T
        if niterin >= itmaxin:
            message = "inner iteration limit reached"
            if warn:
                warnings.warn(message)
            niterin = -niterin
            ret = 2
        elif niterout >= itmaxout:
            message = "iteration limit reached"
            if warn:
                warnings.warn(message)
            niterout = -niterout
            ret = 1
        else:
            ret = 0

    info = {
        "niterout": niterout,
        "errout": errout,
        "inner": {"niterin": niterin, "errin": errin},
    }
    variance = {
        "modelName": kind,
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return {
        "modelName": kind,
        "prior": prior,
        "n": n,
        "d": p,
        "G": G,
        "z": z_new,
        "parameters": parameters,
        "control": control,
        "loglik": loglik,
        "info": info,
        "WARNING": message,
        "returnCode": ret,
    }


def meVEE(data, z, prior=None, control=None, Vinv=None, warn=None, **kwargs):
    """EM for the VEE model (`meVEE` in mclust 6.1.3).

    Returns a dict with the R fields. ``WARNING`` and ``returnCode`` are the
    R attributes of the same names.
    """
    if warn is None:
        warn = mclust_options("warn")
    return _em_ellipsoidal("VEE", data, z, prior, control, Vinv, bool(warn))


def meEVE(data, z, prior=None, control=None, Vinv=None, warn=None, **kwargs):
    """EM for the EVE model (`meEVE` in mclust 6.1.3)."""
    if warn is None:
        warn = mclust_options("warn")
    return _em_ellipsoidal("EVE", data, z, prior, control, Vinv, bool(warn))


def meVVE(data, z, prior=None, control=None, Vinv=None, warn=None, **kwargs):
    """EM for the VVE model (`meVVE` in mclust 6.1.3)."""
    if warn is None:
        warn = mclust_options("warn")
    return _em_ellipsoidal("VVE", data, z, prior, control, Vinv, bool(warn))


def meX(data, prior=None, warn=None, **kwargs):
    """Single-component one-dimensional fit (`meX` is `emX`, which calls `mvnX`)."""
    return mvnX(data, prior=prior, warn=warn, **kwargs)


def meXII(data, prior=None, warn=None, **kwargs):
    """Single-component spherical fit (`meXII` is `emXII`, which calls `mvnXII`)."""
    return mvnXII(data, prior=prior, warn=warn, **kwargs)


def meXXI(data, prior=None, warn=None, **kwargs):
    """Single-component diagonal fit (`meXXI` is `emXXI`, which calls `mvnXXI`)."""
    return mvnXXI(data, prior=prior, warn=warn, **kwargs)


def meXXX(data, prior=None, warn=None, **kwargs):
    """Single-component full fit (`meXXX` is `emXXX`, which calls `mvnXXX`)."""
    return mvnXXX(data, prior=prior, warn=warn, **kwargs)
