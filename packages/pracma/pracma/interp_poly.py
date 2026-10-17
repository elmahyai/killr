"""Polynomial arithmetic, evaluation, and Horner schemes."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.interp_support import (
    as_vector,
    deconv,
    eig_values,
    format_c,
    is_number_or_complex,
    is_numeric_value,
    is_r_matrix,
    is_r_vector,
    r_character_double,
    zapsmall,
)
from pracma.arrays import eye, zeros


def _coeff(value, complex_ok: bool = True) -> np.ndarray:
    if value is None:
        return np.array([], dtype=float)
    if not is_r_vector(value):
        raise PracmaError("vector")
    return as_vector(value, complex_ok=complex_ok)


def _strip(coeffs: np.ndarray) -> np.ndarray:
    while coeffs.size > 1 and coeffs[0] == 0:
        coeffs = coeffs[1:]
    return coeffs


def Poly(x):
    if x is None or np.asarray(x).size == 0:
        return np.array([1.0])
    if is_r_vector(x) and is_number_or_complex(x):
        roots = as_vector(x, complex_ok=True)
    elif is_r_matrix(x) and is_number_or_complex(x):
        roots = np.asarray(eig_values(np.asarray(x, dtype=float))).reshape(-1)
    else:
        raise PracmaError("Argument 'x' must be a vector or square matrix.")
    degree = roots.size
    poly = np.zeros(degree + 1, dtype=complex if np.iscomplexobj(roots) else float)
    poly[0] = 1
    for i in range(degree):
        poly[1 : i + 2] = poly[1 : i + 2] - roots[i] * poly[: i + 1]
    if np.iscomplexobj(poly) and np.all(np.imag(poly) == 0):
        poly = np.real(poly)
    return np.asarray(poly)


def polyadd(p, q):
    if not (is_r_vector(p) and is_number_or_complex(p) and is_r_vector(q) and is_number_or_complex(q)):
        raise PracmaError("Arguments 'p' and 'q' must be real or complex vectors.")
    left = as_vector(p, complex_ok=True)
    right = as_vector(q, complex_ok=True)
    if left.size >= right.size:
        total = left + np.concatenate([np.zeros(left.size - right.size, dtype=left.dtype), right])
    else:
        total = right + np.concatenate([np.zeros(right.size - left.size, dtype=right.dtype), left])
    return _strip(np.array(total))


def polymul(p, q):
    if not (is_r_vector(p) and is_number_or_complex(p) and is_r_vector(q) and is_number_or_complex(q)):
        raise PracmaError("Arguments 'p' and 'q' must be real or complex vectors.")
    left = as_vector(p, complex_ok=True)
    right = as_vector(q, complex_ok=True)
    if left.size <= 1 or right.size <= 1:
        return np.array(np.multiply(left, right)).reshape(-1)
    result = np.zeros(left.size + right.size - 1, dtype=np.result_type(left, right))
    for i, factor in enumerate(right):
        result = result + np.concatenate(
            [np.zeros(i, dtype=result.dtype), left * factor, np.zeros(right.size - i - 1, dtype=result.dtype)]
        )
    return _strip(result)


def polypow(p, n):
    if not (is_r_vector(p) and is_number_or_complex(p)):
        raise PracmaError("Arguments 'p' must be a real or complex vector.")
    if not is_numeric_value(n) or np.asarray(n).size != 1:
        raise PracmaError("Argument 'n' must be a non-negative integer.")
    power = float(np.asarray(n).reshape(-1)[0])
    if math.floor(power) != math.ceil(power) or power < 0:
        raise PracmaError("Argument 'n' must be a non-negative integer.")
    result = np.array([1.0])
    remaining = int(power)
    base = as_vector(p, complex_ok=True)
    while remaining > 0:
        result = polymul(result, base)
        remaining -= 1
    return result


def polydiv(p, q):
    divisor = as_vector(q, complex_ok=True)
    dividend = as_vector(p, complex_ok=True)
    if divisor.size == 1:
        return {"d": dividend / divisor[0], "r": np.array([0.0])}
    parts = deconv(dividend, divisor)
    return {"d": zapsmall(parts["q"]), "r": zapsmall(parts["r"])}


def polyder(p, q=None):
    if q is not None:
        if np.asarray(q).size == 0:
            return np.array([0.0])
        if not is_number_or_complex(q):
            raise PracmaError("Arguments must be real or complex vectors or matrices.")
        second = np.asarray(q)
        if np.iscomplexobj(second):
            second = np.array(second, dtype=complex).reshape(-1)
        else:
            second = np.array(second, dtype=float).reshape(-1)
    else:
        second = np.array([1.0])
    if p is None or np.asarray(p).size == 0:
        return np.array([0.0])
    if not is_number_or_complex(p):
        raise PracmaError("Argument 'p' must be a real or complex vector or matrix.")
    first = np.asarray(p)
    if np.iscomplexobj(first):
        first = np.array(first, dtype=complex).reshape(-1)
    else:
        first = np.array(first, dtype=float).reshape(-1)
    if first.size * second.size <= 1:
        return np.array([0.0])
    result = np.zeros(first.size + second.size - 1, dtype=np.result_type(first, second))
    for i, factor in enumerate(second):
        result = result + np.concatenate(
            [np.zeros(i, dtype=result.dtype), first * factor, np.zeros(second.size - i - 1, dtype=result.dtype)]
        )
    degree = result.size
    result = np.arange(degree - 1, 0, -1, dtype=float) * result[: degree - 1]
    return _strip(np.array(result))


def polyint(p, k=0):
    if p is None or np.asarray(p).size == 0:
        return None
    if not (is_r_vector(p) and is_number_or_complex(p)):
        raise PracmaError("Argument 'p' must be a real or complex vector.")
    if not (is_r_vector(k) and is_number_or_complex(k)):
        raise PracmaError("Argument 'k' must be a real or complex vector")
    coeffs = as_vector(p, complex_ok=True)
    constant = as_vector(k, complex_ok=True)
    integrated = coeffs / np.arange(coeffs.size, 0, -1, dtype=float)
    return np.concatenate([integrated, constant])


def polytrans(p, q):
    if not (is_r_vector(p) and is_number_or_complex(p) and is_r_vector(q) and is_number_or_complex(q)):
        raise PracmaError("Arguments 'p' and 'q' must be real or complex vectors.")
    coeffs = as_vector(p, complex_ok=True)
    other = as_vector(q, complex_ok=True)
    if coeffs.size == 1:
        return coeffs
    total = np.array([0.0])
    degree = coeffs.size
    for i in range(degree):
        total = polyadd(total, coeffs[i] * polypow(other, degree - i - 1))
    return total


def poly2str(p, svar="x", smul="*", d=7):
    if p is None or np.asarray(p).size == 0:
        return ""
    coeffs = np.asarray(p)
    if np.iscomplexobj(coeffs):
        raise PracmaError("Printing of complex coefficients not yet implemented.")
    if not is_numeric_value(coeffs):
        raise PracmaError("Argument 'p' must be a numeric vector.")
    values = np.array(coeffs, dtype=float).reshape(-1)
    values = _strip(values)
    if values.size == 1:
        return r_character_double(float(values[0]))
    signs = np.sign(values)
    texts = [format_c(abs(float(item)), int(d)) for item in values]
    degree = values.size - 1
    sign0 = "" if signs[0] == 1 else "-"
    pieces = f"{sign0}{texts[0]}{smul}{svar}^{degree}"
    for i in range(1, degree + 1):
        if signs[i] == 1:
            joiner = " + "
        elif signs[i] == -1:
            joiner = " - "
        else:
            continue
        power = degree - i
        if power > 1:
            pieces += f"{joiner}{texts[i]}{smul}{svar}^{power}"
        elif power == 1:
            pieces += f"{joiner}{texts[i]}{smul}{svar}"
        else:
            pieces += f"{joiner}{texts[i]}"
    return pieces


def polyval(p, x):
    if x is None or np.asarray(x).size == 0:
        return np.array([])
    if p is None or np.asarray(p).size == 0:
        return 0 * np.asarray(x, dtype=float)
    if not (is_r_vector(p) and is_number_or_complex(p)):
        raise PracmaError("Argument 'p' must be a real or complex vector.")
    if not (is_r_vector(x) or is_r_matrix(x)):
        raise PracmaError("Argument 'x' must be a real or complex matrix.")
    coeffs = as_vector(p, complex_ok=True)
    points = np.asarray(x)
    shape = points.shape if points.ndim == 2 else None
    flat = np.array(points, dtype=np.result_type(points, coeffs)).reshape(-1, order="F" if points.ndim == 2 else "C")
    powers = np.arange(coeffs.size - 1, -1, -1, dtype=float)
    values = (flat.reshape(-1, 1) ** powers) @ coeffs
    result = np.asarray(values).reshape(-1)
    if shape is not None:
        return np.reshape(result, shape, order="F")
    return result


def polyvalm(p, A):
    empty = p is None or np.asarray(p).size == 0
    if not ((is_numeric_value(p) or empty) and is_numeric_value(A)):
        raise PracmaError("is.numeric(p) || isempty(p) is not TRUE")
    if not is_r_vector(p) and not empty:
        raise PracmaError("Argument 'p' must be a numeric vector.")
    matrix = np.asarray(A, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Argument 'A' must be a square matrix.")
    coeffs = np.array([] if empty else np.asarray(p, dtype=float).reshape(-1))
    n = coeffs.size
    if n == 0:
        return zeros(matrix.shape[0])
    if n == 1:
        return np.diag(np.repeat(coeffs[0], n))
    identity = eye(matrix.shape[0])
    value = coeffs[0] * identity
    for coeff in coeffs[1:]:
        value = value @ matrix + coeff * identity
    return value


def horner(p, x):
    if p is None or x is None or np.asarray(p).size == 0 or np.asarray(x).size == 0:
        return None
    coeffs = np.asarray(p, dtype=float).reshape(-1)
    points = np.asarray(x, dtype=float).reshape(-1)
    degree = coeffs.size
    if degree == 0:
        return {"y": np.full(points.shape, np.nan), "dy": np.full(points.shape, np.nan)}
    if degree == 1:
        return {"y": np.full(points.shape, coeffs[0]), "dy": np.zeros(points.shape)}
    value = np.full(points.shape, coeffs[0])
    derivative = np.zeros(points.shape)
    for coeff in coeffs[1:]:
        derivative = derivative * points + value
        value = value * points + coeff
    return {"y": value, "dy": derivative}


def hornerdefl(p, x):
    if p is None or x is None or np.asarray(p).size == 0 or np.asarray(x).size == 0:
        return None
    coeffs = np.asarray(p, dtype=float).reshape(-1)
    point = float(np.asarray(x, dtype=float).reshape(-1)[0])
    quotient = np.zeros(coeffs.size)
    quotient[0] = coeffs[0]
    for j in range(1, coeffs.size):
        quotient[j] = coeffs[j] + quotient[j - 1] * point
    return {"y": np.array([quotient[-1]]), "q": quotient[:-1]}
