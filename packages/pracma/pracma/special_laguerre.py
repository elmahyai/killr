"""Laguerre's method for a polynomial root."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_na, is_numeric_value, length_of
from pracma.special_poly import polyder, polyval

_EPS = float(np.finfo(float).eps ** 0.5)


def laguerre(p, x0, nmax=25, tol=_EPS):
    if not is_numeric_value(p) and not is_complex_value(p):
        raise PracmaError("Argument 'p' must be a numeric or complex vector.")
    if (not is_numeric_value(x0) and not is_complex_value(x0)) or length_of(x0) != 1:
        raise PracmaError("Argument 'x0' must be a real or complex number.")
    coeffs = np.ravel(np.asarray(p), order="F")
    start = np.asarray(x0).reshape(-1)[0]
    degree = coeffs.size - 1
    first = polyder(coeffs)
    second = polyder(first)
    y0 = np.asarray(polyval(coeffs, start)).reshape(-1)[0]
    if abs(y0) < tol:
        return np.array([start])
    root = start
    m = 0
    for m in range(1, int(nmax) + 1):
        a = np.asarray(polyval(first, root)).reshape(-1)[0] / y0
        a2 = a * a
        b = a2 - np.asarray(polyval(second, root)).reshape(-1)[0] / y0
        with np.errstate(invalid="ignore", divide="ignore"):
            root_next = root - degree / (a + a / abs(a) * np.sqrt((degree - 1) * (degree * b - a2)))
        if is_na(root_next):
            raise PracmaError("Start value 'x0' results in an indefinite direction.")
        y = np.asarray(polyval(coeffs, root_next)).reshape(-1)[0]
        root = root_next
        if abs(y) < tol:
            break
        y0 = y
    if m > nmax:
        warnings.warn("Root finding process might not have converged.", RuntimeWarning)
    if np.iscomplexobj(root) and np.imag(root) == 0 and not is_complex_value(p) and not is_complex_value(x0):
        root = np.real(root)
    return np.array([root])
