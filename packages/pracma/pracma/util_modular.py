"""ceil, Fix, mod, rem, idivide, gcd, and Lcm from modular.R."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, match_arg, require


def ceil(n):
    return np.ceil(np.asarray(n, dtype=float))


def Fix(n):
    return np.trunc(np.asarray(n, dtype=float))


def _scalar_modulus(m) -> float:
    require(is_numeric(m), "is.numeric(m) is not TRUE")
    array = np.asarray(m, dtype=float).reshape(-1)
    if array.size != 1:
        raise PracmaError("Argument 'm' must be an integer scalar.")
    number = float(array[0])
    if math.floor(number) != math.ceil(number):
        raise PracmaError("Argument 'm' must be an integer scalar.")
    return number


def mod(n, m):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    modulus = _scalar_modulus(m)
    values = np.asarray(n, dtype=float)
    if modulus == 0:
        return values
    return np.mod(values, modulus)


def rem(n, m):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    modulus = _scalar_modulus(m)
    values = np.asarray(n, dtype=float)
    if modulus == 0:
        return np.full(values.shape, np.nan)
    remainder = np.mod(values, modulus).astype(float, copy=True)
    mask = (remainder != 0) & (np.sign(values) * np.sign(modulus) < 0)
    remainder = np.array(remainder, dtype=float, copy=True)
    remainder[mask] = remainder[mask] - modulus
    return remainder


def idivide(n, m, rounding="fix"):
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    require(is_numeric(m), "is.numeric(m) is not TRUE")
    rounding = match_arg(rounding, ("fix", "floor", "ceil", "round"))
    left = np.asarray(n, dtype=float).reshape(-1)
    right = np.asarray(m, dtype=float).reshape(-1)
    if left.size == 1:
        left = np.repeat(left, right.size)
    elif right.size == 1:
        right = np.repeat(right, left.size)
    if left.size != right.size:
        raise PracmaError("Arguments 'n', 'm' must be scalars or have the same length.")
    if np.any(np.floor(left) != np.ceil(left)) or np.any(np.floor(right) != np.ceil(right)):
        raise PracmaError("Arguments 'n', 'm' must be integers or vectors of integers.")
    quotients = left / right
    if rounding == "fix":
        quotients = Fix(quotients)
    elif rounding == "floor":
        quotients = np.floor(quotients)
    elif rounding == "ceil":
        quotients = np.ceil(quotients)
    else:
        quotients = np.round(quotients)
    return np.asarray(quotients, dtype=float)


def _pair(a, b):
    left = np.asarray(a, dtype=float).reshape(-1)
    right = np.asarray(b, dtype=float).reshape(-1)
    if np.any(np.floor(left) != np.ceil(left)) or np.any(np.floor(right) != np.ceil(right)):
        raise PracmaError("All input arguments must be integer.")
    if left.size == 1:
        left = np.repeat(left, right.size)
    elif right.size == 1:
        right = np.repeat(right, left.size)
    elif left.size != right.size:
        raise PracmaError("Length of 'a' and 'b' must be equal (or one length is 1).")
    return left, right


def gcd(a, b, extended=False):
    require(is_numeric(a), "is.numeric(a) is not TRUE")
    require(is_numeric(b), "is.numeric(b) is not TRUE")
    left, right = _pair(a, b)
    count = left.size
    bezout_a = np.zeros(count)
    bezout_b = np.zeros(count)
    values = np.zeros(count)
    for index in range(count):
        u = np.array([1.0, 0.0, abs(left[index])])
        v = np.array([0.0, 1.0, abs(right[index])])
        while v[2] != 0:
            quote = math.floor(u[2] / v[2])
            nxt = u - v * quote
            u = v
            v = nxt
        sign = np.sign(left[index])
        bezout_a[index] = u[0] * sign
        bezout_b[index] = u[1] * sign
        values[index] = u[2]
    if extended:
        return {"g": values, "c": bezout_a, "d": bezout_b}
    return values


def Lcm(a, b):
    require(is_numeric(a), "is.numeric(a) is not TRUE")
    require(is_numeric(b), "is.numeric(b) is not TRUE")
    left, right = _pair(a, b)
    divisor = gcd(left, right, extended=False)
    return left / divisor * right
