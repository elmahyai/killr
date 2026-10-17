"""Complex-step derivatives."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, require_numeric

_EPS = float(np.finfo(float).eps)


def _bind(f, args, kwargs):
    def fun(x):
        return f(x, *args, **kwargs)
    return fun


def _is_double(value) -> bool:
    if isinstance(value, (bool, np.bool_, int)):
        return False
    array = np.asarray(value)
    return array.dtype == np.float64 or array.dtype == float or np.issubdtype(array.dtype, np.floating)


def complexstep(f, x0, h=1e-20, *args, **kwargs):
    require_numeric(x0, "x0")
    require_numeric(h, "h")
    if not float(np.asarray(h).reshape(-1)[0]) < 1e-15:
        raise PracmaError("h < 1e-15 is not TRUE")
    fun = _bind(f, args, kwargs)
    step = float(np.asarray(h).reshape(-1)[0])
    origin = np.asarray(x0, dtype=float)
    try:
        shifted = fun(origin + step * 1j)
    except Exception as exc:
        raise PracmaError("Function 'f' does not appear to accept complex arguments.") from exc
    plain = fun(origin)
    if not np.iscomplexobj(shifted) or not _is_double(plain):
        from pracma.num_numderiv import numderiv
        warnings.warn("Some maginary part is zero: applied Richardson instead.", stacklevel=2)
        return numderiv(fun, float(np.asarray(origin).reshape(-1)[0]), h=0.1)["df"]
    return np.imag(np.asarray(shifted, dtype=complex)) / step


def grad_csd(f, x0, h=1e-20, *args, **kwargs):
    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    step = float(h)
    value = np.asarray(fun(point)).reshape(-1)
    if value.size > 1:
        raise PracmaError("Funktion 'f' does not return a scalar; call 'Jacobian_csd'.")
    gradient = np.full(point.size, np.nan)
    for index in range(point.size):
        shifted = point.astype(complex)
        shifted[index] = shifted[index] + step * 1j
        gradient[index] = np.imag(np.asarray(fun(shifted), dtype=complex)).reshape(-1)[0] / step
    return gradient


def jacobian_csd(f, x0, h=1e-20, *args, **kwargs):
    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    step = float(h)
    value = np.asarray(fun(point), dtype=float).reshape(-1)
    jac = np.full((value.size, point.size), np.nan)
    for index in range(point.size):
        shifted = point.astype(complex)
        shifted[index] = shifted[index] + step * 1j
        jac[:, index] = np.imag(np.asarray(fun(shifted), dtype=complex)).reshape(-1) / step
    return jac


def hessian_csd(f, x0, h=1e-20, *args, **kwargs):
    from pracma.num_numderiv import numderiv

    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    step = float(h)
    value = np.asarray(fun(point)).reshape(-1)
    if value.size > 1:
        raise PracmaError("Funktion 'f' does not return a scalar, as needed for Hessian.")
    hess = np.full((point.size, point.size), np.nan)
    for i in range(point.size):
        def fi(x, i=i):
            z = np.asarray(x, dtype=complex).copy()
            z[i] = z[i] + step * 1j
            return float(np.imag(np.asarray(fun(z), dtype=complex)).reshape(-1)[0] / step)

        for j in range(point.size):
            def ff(x, j=j, fi=fi):
                xx = point.copy()
                xx[j] = x
                return fi(xx)

            hess[i, j] = numderiv(ff, float(point[j]))["df"]
    return hess


def laplacian_csd(f, x0, h=1e-20, *args, **kwargs):
    from pracma.num_numderiv import numderiv

    fun = _bind(f, args, kwargs)
    point = np.asarray(x0, dtype=float).reshape(-1)
    step = float(h)
    value = np.asarray(fun(point)).reshape(-1)
    if value.size > 1:
        raise PracmaError("Funktion 'f' does not return a scalar, as needed for Lapacian.")
    total = np.full(point.size, np.nan)
    for i in range(point.size):
        def fi(x, i=i):
            z = np.asarray(x, dtype=complex).copy()
            z[i] = z[i] + step * 1j
            return float(np.imag(np.asarray(fun(z), dtype=complex)).reshape(-1)[0] / step)

        def ff(x, i=i, fi=fi):
            xx = point.copy()
            xx[i] = x
            return fi(xx)

        total[i] = numderiv(ff, float(point[i]))["df"]
    return float(np.sum(total))
