"""Exponential and logarithmic integrals."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value, real_if_closed
from pracma.special_poly import polyval

_EPS = np.finfo(float).eps
_EGAMMA = 0.57721566490153286061
_P = np.array(
    [
        -3.602693626336023e-09,
        -4.819538452140960e-07,
        -2.569498322115933e-05,
        -6.973790859534190e-04,
        -1.019573529845792e-02,
        -7.811863559248197e-02,
        -3.012432892762715e-01,
        -7.773807325735529e-01,
        8.267661952366478e00,
    ]
)


def _require(x):
    if not is_numeric_value(x) and not is_complex_value(x):
        raise PracmaError("is.numeric(x) || is.complex(x) is not TRUE")


def expint(x):
    _require(x)
    was_real = not is_complex_value(x)
    values = np.ravel(np.asarray(x, dtype=np.complex128), order="F")
    count = values.size
    y = np.zeros(count, dtype=np.complex128)
    boundary = np.asarray(polyval(_P, np.real(values)), dtype=float).reshape(-1)
    series = np.abs(np.imag(values)) <= boundary
    if np.any(series):
        xk = values[series]
        # +0j keeps a positive imaginary zero, so a negative real uses +i*pi.
        yk = -_EGAMMA - np.log(xk + 0j)
        j = 1
        pterm = np.array(xk, copy=True)
        term = np.array(xk, copy=True)
        while np.any(np.abs(term) > _EPS):
            yk = yk + term
            j += 1
            pterm = -xk * pterm / j
            term = pterm / j
        y[series] = yk
    continued = np.abs(np.imag(values)) > boundary
    if np.any(continued):
        xk = values[continued]
        nk = xk.size
        am2 = np.zeros(nk, dtype=np.complex128)
        bm2 = np.ones(nk, dtype=np.complex128)
        am1 = np.ones(nk, dtype=np.complex128)
        bm1 = np.array(xk, copy=True)
        f = am1 / bm1
        oldf = np.full(nk, np.inf, dtype=np.complex128)
        j = 2
        while np.any(np.abs(f - oldf) > (100.0 * _EPS) * np.abs(f)):
            alpha = (j / 2.0)
            a = am1 + alpha * am2
            b = bm1 + alpha * bm2
            am2 = am1 / b
            bm2 = bm1 / b
            am1 = a / b
            bm1 = np.ones(nk, dtype=np.complex128)
            f = am1
            j += 1
            alpha = (j - 1) / 2.0
            beta = xk
            a = beta * am1 + alpha * am2
            b = beta * bm1 + alpha * bm2
            am2 = am1 / b
            bm2 = bm1 / b
            am1 = a / b
            bm1 = np.ones(nk, dtype=np.complex128)
            oldf = f
            f = am1
            j += 1
        real_cut = (np.real(xk) < 0) & (np.imag(xk) == 0)
        y[continued] = np.exp(-xk) * f - 1j * np.pi * real_cut
    return real_if_closed(y, was_real)


expint_E1 = expint


def expint_Ei(x):
    _require(x)
    was_real = not is_complex_value(x)
    values = np.ravel(np.asarray(x, dtype=np.complex128), order="F")
    base = -expint(-values)
    sign_im = np.sign(np.imag(values))
    y = np.where(sign_im <= 0, base - np.pi * 1j, base + np.pi * 1j)
    return real_if_closed(y, was_real)


def li(x):
    _require(x)
    was_real = not is_complex_value(x)
    values = np.ravel(np.asarray(x, dtype=np.complex128), order="F")
    y = expint_Ei(np.log(values + 0j))
    return real_if_closed(np.asarray(y, dtype=np.complex128), was_real)
