"""Sheather-Jones pilot bandwidth calculations used by locfit."""

import math
import numpy as np


def _dnorms(x, k):
    d = np.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    if k == 0:
        return d
    if k == 1:
        return -x * d
    if k == 2:
        return (x * x - 1.0) * d
    if k == 3:
        return x * (3.0 - x * x) * d
    if k == 4:
        return (3.0 - x * x * (6.0 - x * x)) * d
    if k == 6:
        return (-15.0 + x * x * (45.0 - x * x * (15.0 - x * x))) * d
    raise ValueError("k too large in dnorms")


def sjpi(x, a):
    x = np.asarray(x, dtype=float).reshape(-1)
    alpha = np.asarray(a, dtype=float).reshape(-1) * math.sqrt(2.0)
    n = x.size
    if n < 2:
        raise ValueError("x must contain at least two values")
    m = x[:, None] - x[None, :]
    s = np.array([np.sum(_dnorms(m / ai, 4)) for ai in alpha])
    s = s / (n * (n - 1) * alpha**5)
    h = (s * 2.0 * math.sqrt(math.pi) * n) ** (-0.2)
    lam = np.quantile(x, 0.75) - np.quantile(x, 0.25)
    A = 0.92 * lam * n ** (-1.0 / 7.0)
    B = 0.912 * lam * n ** (-1.0 / 9.0)
    tb = -np.sum(_dnorms(m / B, 6)) / (n * (n - 1) * B**7)
    sa = np.sum(_dnorms(m / A, 4)) / (n * (n - 1) * A**5)
    ah = 1.357 * (sa / tb * h**5) ** (1.0 / 7.0)
    return np.column_stack((h, np.asarray(a, dtype=float).reshape(-1), ah / math.sqrt(2.0), s))
