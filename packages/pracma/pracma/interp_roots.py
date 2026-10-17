"""Polynomial roots, multiplicities, and the greatest common factor."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, zeros
from pracma.interp_poly import polyder, polydiv, polyval
from pracma.interp_support import (
    as_vector,
    compan,
    deconv,
    eig_values,
    is_number_or_complex,
    is_numeric_value,
    is_r_vector,
    pad_zeros,
    which_index,
)


def roots(p):
    if p is None or np.asarray(p).size == 0:
        return np.zeros((0, 0))
    if not (is_r_vector(p) and is_number_or_complex(p)):
        raise PracmaError("Argument p must be a vector of real or complex numbers.")
    coeffs = as_vector(p, complex_ok=True)
    if coeffs.size == 1:
        return np.zeros((0, 0))
    nonzero = which_index(coeffs != 0)
    if nonzero.size == 0:
        return None
    first = int(nonzero[0])
    last = int(nonzero[-1])
    trimmed = coeffs[first - 1 : last]
    trailing = np.zeros(coeffs.size - last)
    companion = compan(trimmed)
    if companion.size == 0:
        values = np.array([])
    elif companion.ndim <= 1:
        values = companion.reshape(-1)
    else:
        values = np.asarray(eig_values(companion)).reshape(-1)
    if trailing.size == 0:
        return values
    return np.concatenate([trailing, values])


def polygcf(p, q, tol=1e-12):
    if not (is_r_vector(p) and is_number_or_complex(p)):
        raise PracmaError("Arguments 'p' must be a real or complex vector.")
    if not (is_r_vector(q) and is_number_or_complex(q)):
        raise PracmaError("Arguments 'q' must be a real or complex vector.")
    left = as_vector(p, complex_ok=True)
    right = as_vector(q, complex_ok=True)
    scale = Norm(left)
    parts = polydiv(left, right)
    remainder = parts["r"]
    if Norm(remainder) > scale * tol:
        parts = polydiv(right, remainder)
        next_remainder = parts["r"]
        if Norm(next_remainder) > scale * tol:
            current = np.array([1.0])
            while Norm(current) > scale * tol:
                parts = polydiv(remainder, next_remainder)
                current = parts["r"]
                remainder = next_remainder
                next_remainder = current
            return remainder
        return remainder
    return right


def rootsmult(p, r, tol=1e-12):
    coeffs = np.asarray(p, dtype=float).reshape(-1)
    scale = Norm(coeffs)
    value = abs(float(np.asarray(polyval(coeffs, r)).reshape(-1)[0]))
    if value > scale * tol:
        warnings.warn("Value 'r' is not root of polynomial 'p'.", stacklevel=2)
        return np.array([0.0])
    count = 0
    while value < scale * tol:
        coeffs = polyder(coeffs)
        value = abs(float(np.asarray(polyval(coeffs, r)).reshape(-1)[0]))
        count += 1
    return np.array([float(count)])


def _flatten_zeros(values, count: int) -> np.ndarray:
    extra = zeros(1, count)
    if extra.size == 0:
        return np.asarray(values).reshape(-1)
    return np.concatenate([np.asarray(values).reshape(-1), np.ravel(extra, order="F")])


def polyroots(p, ntol=1e-4, ztol=1e-8):
    if not is_numeric_value(p):
        raise PracmaError("is.numeric(p) is not TRUE")
    coeffs = np.asarray(p, dtype=float).reshape(-1)
    nonzero = which_index(coeffs != 0)
    if nonzero.size == 0:
        return {"root": np.array([]), "mult": np.array([])}
    minp = int(np.min(nonzero))
    maxp = int(np.max(nonzero))
    zero_mult = coeffs.size - maxp
    trimmed = coeffs[minp - 1 : maxp]
    roots_found = []
    mults = []
    if zero_mult > 0:
        roots_found.append(0.0)
        mults.append(float(zero_mult))
    if trimmed.size < 2:
        return {"root": np.array(roots_found), "mult": np.array(mults)}
    ratio = abs(trimmed[-1] / trimmed[0])
    if ratio < 1:
        trimmed = trimmed[::-1]
    derivative = polyder(trimmed)
    g1 = trimmed / trimmed[0]
    last_nonzero = int(np.max(which_index(derivative != 0)))
    g2 = derivative[:last_nonzero] / derivative[0]
    limit = 2 * trimmed.size
    for _k in range(3, limit + 1):
        gap = g1.size - g2.size
        g3 = _flatten_zeros(g2, gap) - _flatten_zeros(g1, -gap)
        keep = which_index(np.abs(g3) > ztol)
        if keep.size == 0:
            g3 = np.array([0.0])
        else:
            g3 = g3[int(np.min(keep)) - 1 : int(np.max(keep))]
        ren = Norm(g3, np.inf) / Norm(g2, np.inf)
        if ren < ntol:
            break
        if gap >= 0:
            g1 = g2
        g2 = g3 / g3[0]
    quotient = deconv(trimmed, g1)["q"]
    derivative_quotient = deconv(derivative, g1)["q"]
    slope = polyder(quotient)
    found = roots(quotient)
    if found is None or (isinstance(found, np.ndarray) and found.ndim == 2 and found.size == 0):
        found = np.array([])
    found = np.asarray(found, dtype=float).reshape(-1)
    multiplicity = polyval(derivative_quotient, found) / polyval(slope, found)
    if ratio < 1:
        found = found ** -1
    roots_found.extend(np.real(found).tolist())
    mults.extend(np.round(np.abs(np.asarray(multiplicity, dtype=float).reshape(-1))).tolist())
    return {"root": np.array(roots_found, dtype=float), "mult": np.array(mults, dtype=float)}
