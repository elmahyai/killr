"""Shared steps for the Gaussian M-step wrappers meV, meVEI, meVEV, meVII, meVVI, meVVV, and meEVV.

Each public wrapper mirrors the R function of the same name in mclust 6.1.3:
argument checks, the group count from ``Vinv``, the all-missing ``z`` return,
the prior parameters, and the status codes. The numerical work is done by the
``mclust_kernels`` binding built from ``crates/mclust``.

``shapeo`` and ``uncholf`` are Fortran routines in mclust ``mclust.f``. The
``mclust_kernels`` crate does not export them, so they are called through the
already-built ``crates/mclustbootstraplrt`` library, as ``mclust._fortran`` does.
"""

from __future__ import annotations

import ctypes
import warnings
from typing import Any

import numpy as np

from mclust import model_metadata as _model_metadata
from mclust.mclust_options import mclust_options
from mclust.utility_functions import hypvol

# signif(.Machine$double.xmax, 6) and .Machine$double.xmax
XMAX6 = 1.79769e308
DOUBLE_XMAX = 1.7976931348623157e308
INT_MAX = 2147483647


def kernels():
    """Return the ``mclust_kernels`` binding. Each kernel takes one tuple of arguments."""
    import mclust_kernels

    return mclust_kernels


def default_control(control: Any) -> Any:
    if control is None:
        from mclust.em_control import em_control

        return em_control()
    return control


def control_values(control: Any) -> tuple[bool, float, list[float], list[int]]:
    """Return ``equalPro``, ``eps``, ``tol`` (length 2), and ``itmax`` (length 2)."""
    eps = float(np.ravel(control["eps"])[0])
    tol = [float(v) for v in np.ravel(control["tol"])]
    itmax = [int(v) for v in np.ravel(control["itmax"])]
    while len(tol) < 2:
        tol.append(tol[-1])
    while len(itmax) < 2:
        itmax.append(INT_MAX)
    return bool(control["equalPro"]), eps, tol, itmax


def resolve_warn(warn: Any) -> bool:
    if warn is None:
        return bool(mclust_options("warn"))
    return bool(warn)


def emit(warn: bool, message: str) -> None:
    if warn:
        warnings.warn(message, RuntimeWarning, stacklevel=3)


def data_matrix(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim != 2 or x.shape[1] == 1:
        raise ValueError("data should in the form of a matrix")
    return x


def data_vector(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim > 2 or (x.ndim == 2 and x.shape[1] != 1):
        raise ValueError("data must be one-dimensional")
    return x.reshape(-1)


def z_matrix(z: Any, n: int, message: str) -> np.ndarray:
    zz = np.asarray(z, dtype=float)
    if zz.ndim < 2:
        zz = zz.reshape(-1, 1)
    if zz.ndim != 2 or zz.shape[0] != n:
        raise ValueError(message)
    return zz


def check_z(zz: np.ndarray) -> None:
    if np.any(np.isnan(zz)) or np.any(zz < 0) or np.any(zz > 1):
        raise ValueError("improper specification of z")


def group_count(K: int, Vinv: Any, data: np.ndarray) -> tuple[int, float | None]:
    """Return ``G`` and ``Vinv``. With ``Vinv`` given, ``G`` is ``K - 1``."""
    if Vinv is None:
        return K, None
    G = K - 1
    value = float(Vinv)
    if value <= 0:
        value = float(hypvol(data, reciprocal=True))
    return G, value


def vinv_arg(Vinv: float | None) -> float:
    return -1.0 if Vinv is None else float(Vinv)


def prior_params(prior: dict, data: Any, G: int, model_name: str) -> dict:
    """Call the prior function named in ``prior``, the R ``do.call`` step."""
    name = prior.get("functionName", "defaultPrior")
    func = name if callable(name) else getattr(_model_metadata, str(name))
    kwargs = {key: value for key, value in prior.items() if key != "functionName"}
    return func(data=data, G=G, modelName=model_name, **kwargs)


def scalar(value: Any) -> float:
    return float(np.ravel(np.asarray(value, dtype=float))[0])


def fflat(a: Any) -> list[float]:
    """Flatten in column-major order, the layout ``.Fortran`` uses."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def farr(values: Any, shape: tuple[int, ...]) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(shape, order="F")


def nan_like(shape: Any) -> np.ndarray:
    return np.full(shape, np.nan)


def underflow_text(equal_pro: bool, eqpro_word: str = "z column sum") -> str:
    if equal_pro:
        return f"{eqpro_word} fell below threshold"
    return "mixing proportion fell below threshold"


def r_chol(S: np.ndarray) -> np.ndarray:
    """R ``chol``: the upper triangular ``U`` with ``t(U) %*% U == S``."""
    return np.linalg.cholesky(np.asarray(S, dtype=float)).T


def _fortran_lib():
    from mclust._fortran import lib

    return lib()


def _dptr(a: np.ndarray):
    return a.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def fortran_uncholf(upper: bool, x: np.ndarray) -> np.ndarray:
    """Fortran ``uncholf``, the body of R ``unchol``. Returns a new array."""
    buf = np.array(x, dtype=float, order="F")
    nrow, ncol = buf.shape
    flag = ctypes.c_int(1 if upper else 0)
    nr = ctypes.c_int(nrow)
    nc = ctypes.c_int(ncol)
    info = ctypes.c_int(0)
    _fortran_lib().uncholf_(
        ctypes.byref(flag), _dptr(buf), ctypes.byref(nr), ctypes.byref(nc), ctypes.byref(info)
    )
    return buf


def fortran_shapeo(shape: Any, O: np.ndarray) -> np.ndarray:
    """Fortran ``shapeo`` with ``transpose = FALSE``, the body of R ``shapeO``."""
    buf = np.array(O, dtype=float, order="F")
    s = np.array(shape, dtype=float, order="F").reshape(-1)
    l, m = buf.shape[0], buf.shape[2]
    work = np.zeros(l * l, dtype=float)
    transp = ctypes.c_int(0)
    lc = ctypes.c_int(l)
    mc = ctypes.c_int(m)
    info = ctypes.c_int(0)
    _fortran_lib().shapeo_(
        ctypes.byref(transp),
        _dptr(s),
        _dptr(buf),
        ctypes.byref(lc),
        ctypes.byref(mc),
        _dptr(work),
        ctypes.byref(info),
    )
    return buf


def build_result(
    model: str,
    prior: Any,
    n: int,
    d: int,
    G: int,
    z: np.ndarray,
    parameters: dict,
    control: Any,
    loglik: float,
    info: Any,
    warning: str | None,
    return_code: int,
) -> dict:
    """The named list R returns: the fields, then ``info``, ``WARNING``, ``returnCode``."""
    return {
        "modelName": model,
        "prior": prior,
        "n": n,
        "d": d,
        "G": G,
        "z": z,
        "parameters": parameters,
        "control": control,
        "loglik": loglik,
        "info": info,
        "WARNING": warning,
        "returnCode": return_code,
    }


def unpack_inner(itmax_out: Any, tol_out: Any) -> tuple[int, int, float, float]:
    """Outer and inner iteration counts and errors from the two-element vectors."""
    return int(itmax_out[0]), int(itmax_out[1]), float(tol_out[0]), float(tol_out[1])
