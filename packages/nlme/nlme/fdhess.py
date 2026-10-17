"""Finite-difference gradient and Hessian from nlme."""

from __future__ import annotations

import sys

import numpy as np


def fdHess(pars, fun, *args, relStep=None, minAbsPar=0, **kwargs):
    """Approximate the value, gradient, and Hessian of a scalar function.

    ``relStep`` is R's ``.relStep``. The default step is the cube root of
    machine epsilon. The fit is a Koschal design: a center, a step along
    each axis in both directions, and one step along each pair of axes.
    The pure second-derivative coefficient is doubled when the transpose
    fills the upper triangle.
    """
    if relStep is None:
        relStep = sys.float_info.epsilon ** (1.0 / 3.0)
    point = _as_numeric(pars)
    npar = int(point.size)
    incr = np.maximum(np.abs(point), _recycle(minAbsPar, npar)) * _recycle(
        relStep, npar
    )
    directions, scale = _directions(incr)
    shifted = point[:, None] + incr[:, None] * directions
    observed = np.empty(directions.shape[1], dtype=np.float64)
    for column in range(directions.shape[1]):
        sample = np.array(shifted[:, column], dtype=np.float64, copy=True)
        observed[column] = _scalar(fun(sample, *args, **kwargs))
    coded = directions.T
    design = _model(coded)
    coefs = np.linalg.solve(design, observed) / scale
    return {
        "mean": coefs[0],
        "gradient": np.array(coefs[1 : 1 + npar], dtype=np.float64, copy=True),
        "Hessian": _hessian(coefs, npar),
    }


def _as_numeric(pars):
    array = np.asarray(pars, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1)
    if array.ndim == 1:
        return np.array(array, dtype=np.float64, copy=True)
    return np.ravel(array, order="F")


def _recycle(values, n):
    array = np.asarray(values, dtype=np.float64)
    flat = array.reshape(-1) if array.ndim <= 1 else np.ravel(array, order="F")
    if n == 0:
        return np.zeros(0, dtype=np.float64)
    if flat.size == 1:
        return np.full(n, flat[0], dtype=np.float64)
    if flat.size == n:
        return np.array(flat, dtype=np.float64, copy=True)
    return np.resize(flat, n).astype(np.float64, copy=False)


def _directions(incr):
    npar = int(incr.size)
    if npar == 0:
        return np.zeros((0, 1), dtype=np.float64), np.ones(1, dtype=np.float64)
    # The scale is c(1, incr, incr^2, incr[i] * incr[j]). Those blocks
    # have the same lengths as the center, the two axial steps, and the pairs.
    eye = np.eye(npar, dtype=np.float64)
    columns = [np.zeros(npar, dtype=np.float64)]
    scale = [1.0]
    for j in range(npar):
        columns.append(eye[:, j])
        scale.append(incr[j])
    for j in range(npar):
        columns.append(-eye[:, j])
        scale.append(incr[j] * incr[j])
    for i in range(npar - 1):
        for j in range(i + 1, npar):
            columns.append(eye[:, i] + eye[:, j])
            scale.append(incr[i] * incr[j])
    return np.column_stack(columns), np.asarray(scale, dtype=np.float64)


def _model(coded):
    rows, npar = coded.shape
    parts = [np.ones((rows, 1), dtype=np.float64), coded, coded * coded]
    for i in range(npar - 1):
        parts.append(coded[:, i : i + 1] * coded[:, i + 1 :])
    return np.column_stack(parts)


def _hessian(coefs, npar):
    hess = np.zeros((npar, npar), dtype=np.float64)
    if npar == 0:
        return hess
    diagonal = coefs[npar + 1 : 2 * npar + 1]
    for j in range(npar):
        hess[j, j] = diagonal[j]
    cross = coefs[2 * npar + 1 :]
    k = 0
    for col in range(npar):
        for row in range(col + 1, npar):
            hess[row, col] = cross[k]
            k += 1
    return hess + hess.T


def _scalar(value):
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if array.size != 1:
        raise ValueError("fun must return a numeric scalar")
    return float(array[0])
