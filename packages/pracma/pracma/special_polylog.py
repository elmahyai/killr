"""Polylogarithm."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_numeric_value, length_of, stop_unless


def _gamma_r(value):
    if value <= 0.0 and value == math.floor(value):
        return math.nan
    return math.gamma(value)


def polylog(z, n):
    stop_unless(is_numeric_value(z), "is.numeric(z) is not TRUE")
    stop_unless(is_numeric_value(n), "is.numeric(n) is not TRUE")
    if length_of(n) != 1 or math.floor(float(n)) != math.ceil(float(n)) or float(n) < -4:
        raise PracmaError("Argument 'n' must be a natural number n >= -4 .")
    if length_of(z) > 1 or abs(float(np.asarray(z).reshape(-1)[0])) >= 1:
        raise PracmaError("Argument 'z' must be a single real number with abs(z) < 1 .")
    n = float(n)
    z = float(np.asarray(z).reshape(-1)[0])

    def zeta_(x):
        def eta_(power, terms):
            total = 0.0
            for k in range(1, terms + 1):
                total += ((-1) ** (k + 1)) / k ** power
            return total

        prefactor = 2 ** (x - 1) / (2 ** (x - 1) - 1)
        numerator = (
            1
            + 36 * 2**x * eta_(x, 2)
            + 315 * 3**x * eta_(x, 3)
            + 1120 * 4**x * eta_(x, 4)
            + 1890 * 5**x * eta_(x, 5)
            + 1512 * 6**x * eta_(x, 6)
            + 462 * 7**x * eta_(x, 7)
        )
        denominator = (
            1
            + 36 * 2**x
            + 315 * 3**x
            + 1120 * 4**x
            + 1890 * 5**x
            + 1512 * 6**x
            + 462 * 7**x
        )
        return prefactor * numerator / denominator

    def b(i):
        return zeta_(n - i)

    def s_partial(power, base, terms):
        total = 0.0
        for k in range(1, terms + 1):
            total += base**k / k**power
        return total

    alpha = -math.log(z)
    if abs(z) > 0.55:
        preterm = _gamma_r(1.0 - n) / alpha ** (1.0 - n)
        b0, b1, b2, b3, b4 = b(0), b(1), b(2), b(3), b(4)
        nominator = (
            b0
            - alpha * (b1 - 4 * b0 * b4 / 7 / b3)
            + alpha**2 * (b2 / 2 + b0 * b4 / 7 / b2 - 4 * b1 * b4 / 7 / b3)
            - alpha**3 * (b3 / 6 - 2 * b0 * b4 / 105 / b1 + b1 * b4 / 7 / b2 - 2 * b2 * b4 / 7 / b3)
        )
        denominator = (
            1
            + alpha * 4 * b4 / 7 / b3
            + alpha**2 * b4 / 7 / b2
            + alpha**3 * 2 * b4 / 105 / b1
            + alpha**4 * b4 / 840 / b0
        )
        y = preterm + nominator / denominator
    else:
        nominator = (
            6435 * 9**n * s_partial(n, z, 8)
            - 27456 * 8**n * z * s_partial(n, z, 7)
            + 48048 * 7**n * z**2 * s_partial(n, z, 6)
            - 44352 * 6**n * z**3 * s_partial(n, z, 5)
            + 23100 * 5**n * z**4 * s_partial(n, z, 4)
            - 6720 * 4**n * z**5 * s_partial(n, z, 3)
            + 1008 * 3**n * z**6 * s_partial(n, z, 2)
            - 64 * 2**n * z**7 * s_partial(n, z, 1)
        )
        denominator = (
            6435 * 9**n
            - 27456 * 8**n * z
            + 48048 * 7**n * z**2
            - 44352 * 6**n * z**3
            + 23100 * 5**n * z**4
            - 6720 * 4**n * z**5
            + 1008 * 3**n * z**6
            - 64 * 2**n * z**7
            + z**8
        )
        y = nominator / denominator
    return np.array([y], dtype=float)
