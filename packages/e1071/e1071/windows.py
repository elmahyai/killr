"""Window vectors."""

from __future__ import annotations

import math


def hamming_window(n):
    if n == 1:
        return [1.0]
    width = n - 1
    return [0.54 - 0.46 * math.cos(2 * math.pi * i / width) for i in range(n)]


def hanning_window(n):
    if n == 1:
        return [1.0]
    width = n - 1
    return [0.5 - 0.5 * math.cos(2 * math.pi * i / width) for i in range(n)]


def rectangle_window(n):
    return [1.0] * n
