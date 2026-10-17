"""Cox partial likelihood fit (survival coxfit6.c via Rust eval + BFGS)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

try:
    from coxfit6 import coxfit6_eval_py as _eval
    from coxfit6 import coxmart_py as _rust_coxmart
except ImportError:
    _eval = None
    _rust_coxmart = None


def _chinv2(matrix: np.ndarray) -> None:
    n = matrix.shape[0]
    values = matrix
    for i in range(n):
        pivot = values[i, i]
        if pivot > 0:
            values[i, i] = 1.0 / pivot
            for j in range(i + 1, n):
                values[j, i] = -values[j, i]
                for k in range(i):
                    values[j, k] += values[j, i] * values[i, k]
    for i in range(n):
        if values[i, i] == 0:
            for j in range(i):
                values[j, i] = 0.0
            for j in range(i, n):
                values[i, j] = 0.0
        else:
            for j in range(i + 1, n):
                temp = values[j, i] * values[j, j]
                if j != i:
                    values[i, j] = temp
                for k in range(i, j):
                    values[i, k] += temp * values[j, k]


def coxfit6(
    *,
    maxiter: int,
    time: np.ndarray,
    status: np.ndarray,
    x: np.ndarray,
    offset: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    method: str,
    eps: float,
    toler_chol: float,
    init: np.ndarray | None = None,
    doscale: np.ndarray | None = None,
) -> dict[str, Any]:
    del toler_chol
    if _eval is None:
        raise RuntimeError("install the coxfit6 Rust extension")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    nvar = x.shape[1]
    if init is None:
        beta0 = np.zeros(nvar, dtype=float)
    else:
        beta0 = np.asarray(init, dtype=float).reshape(-1).copy()
    doscale_arr = None if doscale is None else np.asarray(doscale, dtype=np.int32)
    meth = str(method)
    strata = np.asarray(strata, dtype=np.int32).copy()
    time = np.asarray(time, dtype=float)
    status = np.asarray(status, dtype=np.int32)
    offset = np.asarray(offset, dtype=float)
    weights = np.asarray(weights, dtype=float)
    cache: dict[str, Any] = {}

    def evaluate(beta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ll, u, imat, means, scales = _eval(
            time, status, x, offset, weights, strata, meth, beta, doscale_arr
        )
        return (
            float(ll),
            np.asarray(u, dtype=float),
            np.asarray(imat, dtype=float),
            np.asarray(means, dtype=float),
            np.asarray(scales, dtype=float),
        )

    loglik0, u0, imat0, means0, scales0 = evaluate(beta0)
    cache["0"] = (loglik0, u0, imat0, means0, scales0)

    def objective(beta: np.ndarray) -> float:
        key = beta.tobytes()
        if key not in cache:
            cache[key] = evaluate(beta)
        return -cache[key][0]

    def gradient(beta: np.ndarray) -> np.ndarray:
        key = beta.tobytes()
        if key not in cache:
            cache[key] = evaluate(beta)
        return -cache[key][1]

    if maxiter == 0:
        var = imat0.copy()
        _chinv2(var)
        return _pack(beta0, means0, u0, var.reshape(-1), np.array([loglik0, loglik0]), 0.0, 0, 0, scales0)

    result = minimize(
        objective,
        beta0,
        method="BFGS",
        jac=gradient,
        options={"maxiter": maxiter, "gtol": eps},
    )
    beta = np.asarray(result.x, dtype=float)
    loglik1, u, imat, means, scales = evaluate(beta)
    beta_out = beta * scales
    var = imat.copy()
    _chinv2(var)
    for i in range(nvar):
        for j in range(nvar):
            var[i, j] *= scales[i] * scales[j]
    sctest = float(np.dot(u0, u0))
    flag = 0 if result.success else 1000
    return _pack(
        beta_out,
        means,
        u / scales,
        var.reshape(-1),
        np.array([loglik0, loglik1], dtype=float),
        sctest,
        int(result.nit),
        flag,
        scales,
    )


def _pack(beta, means, u, imat, loglik, sctest, it, flag, scales):
    return {
        "coef": np.asarray(beta, dtype=float),
        "means": np.asarray(means, dtype=float),
        "u": np.asarray(u, dtype=float),
        "imat": np.asarray(imat, dtype=float).reshape(-1),
        "loglik": np.asarray(loglik, dtype=float),
        "sctest": float(sctest),
        "iter": int(it),
        "flag": int(flag),
    }


def coxmart(**kwargs: Any) -> np.ndarray:
    if _rust_coxmart is None:
        raise RuntimeError("install the coxfit6 Rust extension")
    return np.asarray(
        _rust_coxmart(
            np.asarray(kwargs["time"], dtype=float),
            np.asarray(kwargs["status"], dtype=np.int32),
            np.asarray(kwargs["strata"], dtype=np.int32).copy(),
            np.asarray(kwargs["score"], dtype=float),
            np.asarray(kwargs["weights"], dtype=float),
            bool(kwargs.get("method_efron", False)),
        ),
        dtype=float,
    )
