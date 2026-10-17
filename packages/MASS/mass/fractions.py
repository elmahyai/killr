"""Continued-fraction display, from MASS fractions and rational."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Fractions:
    """A numeric vector with the fraction strings MASS stores in fracs."""

    values: np.ndarray
    fracs: list[str]

    def __iter__(self):
        return iter(self.values.tolist())


def _rat(x, cycles: int = 10, max_denominator: int = 2000):
    values = np.asarray(x, dtype=float).reshape(-1)
    n = values.size
    a0 = np.zeros(n)
    b0 = np.ones(n)
    finite = np.isfinite(values)
    columns_a = [b0.copy()]
    columns_b = [np.floor(values)]
    remainder = values - columns_b[0]
    length = 0
    while True:
        which = finite & (remainder > 1.0 / max_denominator)
        length += 1
        if not np.any(which) or length > cycles:
            break
        a = a0.copy()
        b = b0.copy()
        a[which] = 1.0
        remainder = remainder.copy()
        remainder[which] = 1.0 / remainder[which]
        b[which] = np.floor(remainder[which])
        remainder[which] = remainder[which] - b[which]
        columns_a.append(a)
        columns_b.append(b)
    pq1 = np.column_stack([b0, a0])
    pq = np.column_stack([columns_b[0], b0])
    for index in range(1, len(columns_b)):
        pq0 = pq1
        pq1 = pq
        b_col = columns_b[index][:, None]
        a_col = columns_a[index][:, None]
        pq = b_col * pq1 + a_col * pq0
    pq = pq.copy()
    pq[~finite, 0] = values[~finite]
    return pq, values


def rational(x, cycles: int = 10, max_denominator: int = 2000):
    """The continued-fraction approximation as a numeric vector."""
    pq, _values = _rat(x, cycles, max_denominator)
    return pq[:, 0] / pq[:, 1]


def fractions(x, cycles: int = 10, max_denominator: int = 2000) -> Fractions:
    """The continued-fraction strings MASS prints for a numeric vector."""
    if isinstance(x, Fractions):
        return x
    pq, values = _rat(x, cycles, max_denominator)
    labels = [f"{int(num)}/{int(den)}" for num, den in pq]
    for index, den in enumerate(pq[:, 1]):
        if den == 1:
            labels[index] = str(int(pq[index, 0]))
    return Fractions(values.copy(), labels)


def as_fractions(x) -> Fractions:
    """Return x when it is already fractions, otherwise convert it."""
    if isinstance(x, Fractions):
        return x
    return fractions(x)


def is_fractions(f) -> bool:
    """Whether f is a fractions result."""
    return isinstance(f, Fractions)
