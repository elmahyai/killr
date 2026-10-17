"""ctypes bindings to mclust 6.1.3 Fortran (CRAN)."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import numpy as np

_LIB: ctypes.CDLL | None = None


def _lib_path() -> Path:
    env = Path(__file__).resolve().parents[3] / "crates" / "mclustbootstraplrt" / "libmclust_fortran.so"
    if env.is_file():
        return env
    raise FileNotFoundError(f"mclust Fortran shared library not found at {env}")


def lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is None:
        _LIB = ctypes.CDLL(str(_lib_path()))
    return _LIB


def _f64(a: np.ndarray) -> np.ndarray:
    return np.asfortranarray(np.asarray(a, dtype=float))


def _i32(x: int) -> ctypes.c_int:
    return ctypes.c_int(int(x))


def eseee(
    data: np.ndarray,
    mu: np.ndarray,
    chol_sigma: np.ndarray,
    pro: np.ndarray,
    vinv: float = -1.0,
) -> tuple[np.ndarray, float, int]:
    data = _f64(data)
    mu = _f64(mu)
    chol_sigma = _f64(chol_sigma)
    pro = np.asarray(pro, dtype=float)
    n, p = data.shape
    g = mu.shape[1]
    k = g
    flag = ctypes.c_int(1)
    vinv_v = ctypes.c_double(vinv)
    work = np.zeros(p, dtype=float, order="F")
    loglik = np.zeros(1, dtype=float, order="F")
    z = np.zeros(n * k, dtype=float, order="F")
    lib().eseee_(
        ctypes.byref(flag),
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        chol_sigma.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        pro.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        _i32(n),
        _i32(p),
        _i32(g),
        ctypes.byref(vinv_v),
        work.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        loglik.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    lapack = int(work[0])
    return z.reshape(n, k, order="F"), float(loglik[0]), lapack


if __name__ == "__main__":
    set_seed = None
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
    from boot.rng import set_seed as _ss

    _ss(42)
    rng = np.random.default_rng()
    data = np.vstack(
        [
            np.column_stack([rng.normal(0, 1, 15), rng.normal(0, 1, 15)]),
            np.column_stack([rng.normal(3, 1, 15), rng.normal(3, 1, 15)]),
        ]
    )
    # use R-fitted params from proof run
    mu = np.array([[0.559420826116684, 2.54314503806674], [-0.467814575886903, 3.14682903410762]], order="F")
    chol = np.array([[-1.07335473142136, 0.0], [-0.186004070332036, -1.03962007933205]], order="F")
    pro = np.array([0.4900171, 0.5099829])
    z, ll, info = eseee(data, mu, chol, pro)
    print(ll, info)
