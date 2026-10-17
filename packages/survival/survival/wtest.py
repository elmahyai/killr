"""Cholesky Wald test used by coxph."""

import math

import numpy as np


def _cholesky2(matrix, toler):
    """FDF' factorization. C indexes columns first, which is R's storage."""
    n = matrix.shape[0]
    values = np.array(matrix, dtype=float, copy=True)

    def get(col, row):
        return values[row, col]

    def setv(col, row, value):
        values[row, col] = value

    eps = 0.0
    for i in range(n):
        if get(i, i) > eps:
            eps = get(i, i)
        for j in range(i + 1, n):
            setv(j, i, get(i, j))
    eps = toler if eps == 0.0 else eps * toler
    for i in range(n):
        pivot = get(i, i)
        if not math.isfinite(pivot) or pivot < eps:
            setv(i, i, 0.0)
        else:
            for j in range(i + 1, n):
                temp = get(j, i) / pivot
                setv(j, i, temp)
                setv(j, j, get(j, j) - temp * temp * pivot)
                for k in range(j + 1, n):
                    setv(k, j, get(k, j) - temp * get(k, i))
    return values


def _chsolve2(factor, y):
    """Solve using the cholesky2 factor. factor[col, row] is the C index."""
    n = y.size
    for i in range(n):
        temp = y[i]
        for j in range(i):
            temp -= y[j] * factor[i, j]
        y[i] = temp
    for i in range(n - 1, -1, -1):
        if factor[i, i] == 0.0:
            y[i] = 0.0
        else:
            temp = y[i] / factor[i, i]
            for j in range(i + 1, n):
                temp -= y[j] * factor[j, i]
            y[i] = temp
    return y


def coxph_wtest(var, b, toler_chol=1e-9):
    """Wald statistic b' V^{-1} b. A zero pivot drops that coefficient."""
    coefficient = np.array(b, dtype=float, copy=True)
    variance = np.array(var, dtype=float, copy=True)
    if coefficient.ndim == 0:
        coefficient = coefficient.reshape(1)
    if np.any(np.isnan(coefficient)):
        keep = ~np.isnan(coefficient if coefficient.ndim == 1 else np.any(np.isnan(coefficient), axis=1))
        if coefficient.ndim == 1:
            keep = ~np.isnan(coefficient)
            coefficient = coefficient[keep]
            if variance.ndim == 2:
                variance = variance[np.ix_(keep, keep)]
        else:
            keep = ~np.any(np.isnan(coefficient), axis=1)
            coefficient = coefficient[keep]
            variance = variance[np.ix_(keep, keep)]
    if coefficient.ndim == 2:
        nvar = coefficient.shape[0]
        ntest = coefficient.shape[1]
    else:
        nvar = coefficient.size
        ntest = 1
        coefficient = coefficient.reshape(nvar, 1)
    if variance.size == 0:
        if nvar == 0:
            return {"test": np.array([]), "df": 0, "solve": 0}
        raise ValueError("Argument lengths do not match")
    if variance.size == 1:
        if nvar == 1:
            value = float(variance.reshape(-1)[0])
            solved = coefficient / value
            return {"test": float(np.sum(coefficient[:, 0] * solved[:, 0])), "df": 1, "solve": solved.reshape(-1)}
        raise ValueError("Argument lengths do not match")
    if variance.ndim != 2 or variance.shape[0] != variance.shape[1]:
        raise ValueError("First argument must be a square matrix")
    if variance.shape[0] != nvar:
        raise ValueError("Argument lengths do not match")
    if not np.all(np.isfinite(coefficient)) or not np.all(np.isfinite(variance)):
        raise ValueError("infinite argument in coxph.wtest")
    factor = _cholesky2(variance, toler_chol)
    df = int(np.sum(np.diag(factor) > 0))
    # _cholesky2 stores the R matrix. C indexes matrix[col][row], so transpose.
    stored = factor.T
    tests = np.empty(ntest)
    solved = np.empty((nvar, ntest))
    for i in range(ntest):
        y = coefficient[:, i].copy()
        _chsolve2(stored, y)
        tests[i] = float(np.dot(coefficient[:, i], y))
        solved[:, i] = y
    if ntest == 1:
        return {"test": float(tests[0]), "df": df, "solve": solved[:, 0].copy()}
    return {"test": tests, "df": df, "solve": solved}
