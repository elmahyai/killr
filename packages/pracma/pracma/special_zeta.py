"""Dirichlet eta and Riemann zeta."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value
from pracma.special_gamma import gammaz

_CC = np.array(
    [
        0.99999999999999999997,
        -0.99999999999999999821,
        0.99999999999999994183,
        -0.99999999999999875788,
        0.99999999999998040668,
        -0.99999999999975652196,
        0.99999999999751767484,
        -0.99999999997864739190,
        0.99999999984183784058,
        -0.99999999897537734890,
        0.99999999412319859549,
        -0.99999996986230482845,
        0.99999986068828287678,
        -0.99999941559419338151,
        0.99999776238757525623,
        -0.99999214148507363026,
        0.99997457616475604912,
        -0.99992394671207596228,
        0.99978893483826239739,
        -0.99945495809777621055,
        0.99868681159465798081,
        -0.99704078337369034566,
        0.99374872693175507536,
        -0.98759401271422391785,
        0.97682326283354439220,
        -0.95915923302922997013,
        0.93198380256105393618,
        -0.89273040299591077603,
        0.83945793215750220154,
        -0.77148960729470505477,
        0.68992761745934847866,
        -0.59784149990330073143,
        0.50000000000000000000,
        -0.40215850009669926857,
        0.31007238254065152134,
        -0.22851039270529494523,
        0.16054206784249779846,
        -0.10726959700408922397,
        0.68016197438946063823e-1,
        -0.40840766970770029873e-1,
        0.23176737166455607805e-1,
        -0.12405987285776082154e-1,
        0.62512730682449246388e-2,
        -0.29592166263096543401e-2,
        0.13131884053420191908e-2,
        -0.54504190222378945440e-3,
        0.21106516173760261250e-3,
        -0.76053287924037718971e-4,
        0.25423835243950883896e-4,
        -0.78585149263697370338e-5,
        0.22376124247437700378e-5,
        -0.58440580661848562719e-6,
        0.13931171712321674741e-6,
        -0.30137695171547022183e-7,
        0.58768014045093054654e-8,
        -0.10246226511017621219e-8,
        0.15816215942184366772e-9,
        -0.21352608103961806529e-10,
        0.24823251635643084345e-11,
        -0.24347803504257137241e-12,
        0.19593322190397666205e-13,
        -0.12421162189080181548e-14,
        0.58167446553847312884e-16,
        -0.17889335846010823161e-17,
        0.27105054312137610850e-19,
    ]
)


def eta(z):
    if not is_numeric_value(z) and not is_complex_value(z):
        raise PracmaError("Argument 'z' must be a real or complex vector.")
    was_real = not is_complex_value(z)
    original = np.ravel(np.asarray(z, dtype=np.float64 if was_real else np.complex128), order="F")
    work = np.array(original, dtype=np.complex128 if not was_real else np.float64, copy=True)
    i0 = original == 0
    rounded = np.round(original / 2.0) * 2.0
    i2 = (original == rounded) & (np.real(original) < 0) & (np.imag(np.asarray(original, dtype=np.complex128)) == 0)
    left = np.real(original) < 0.5
    if np.any(left):
        work = np.array(work, copy=True)
        work[left] = 1.0 - original[left]
    coeffs = _CC[::-1]
    degrees = np.arange(coeffs.size, 0, -1, dtype=float)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        powered = degrees[:, None] ** (-np.asarray(work, dtype=np.complex128 if not was_real else np.float64))[None, :]
        f = coeffs @ powered
        if np.any(left):
            zz = np.asarray(work[left])
            t = (2.0 - 2.0 ** (zz + 1.0)) / (2.0 ** zz - 2.0) / (np.pi ** zz)
            reflected = np.asarray(gammaz(zz)).reshape(-1)
            f = np.array(f, copy=True)
            f[left] = t * np.cos(np.pi / 2.0 * zz) * reflected * f[left]
            if np.any(i0):
                f[i0] = 0.5
            if np.any(i2):
                f[i2] = 0.0
    if was_real:
        return np.real(f).astype(float)
    return f


def zeta(z):
    was_real = not is_complex_value(z)
    values = np.ravel(np.asarray(z), order="F")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        scale = 2.0 ** values
        f = np.asarray(scale / (scale - 2.0) * eta(values))
        pole = values == 1
        if np.any(pole):
            f = np.array(f, dtype=np.result_type(f.dtype, np.float64), copy=True)
            f[pole] = np.inf
    if was_real:
        return np.real(np.asarray(f, dtype=np.complex128)).astype(float)
    return f
