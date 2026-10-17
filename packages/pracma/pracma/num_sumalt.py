"""Cohen-Villegas-Zagier acceleration of an alternating series."""

from __future__ import annotations

import numpy as np


def sumalt(f_alt, n):
    count = int(n)
    b = 2.0 ** (2 * count - 1)
    c = b
    total = 0.0
    for k in range(count - 1, -1, -1):
        total = total + c * float(f_alt(k))
        b = b * (2 * k + 1) * (k + 1) / (2 * (count - k) * (count + k))
        c = c + b
    return float(total / c)
