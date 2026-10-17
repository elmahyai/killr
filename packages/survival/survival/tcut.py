"""Time-dependent cutpoints (survival::tcut)."""

from __future__ import annotations

import numpy as np

from survival.formatreal import format_real


class Tcut:
    """Numeric values with cutpoints and labels (R class ``tcut``)."""

    __slots__ = ("values", "cutpoints", "labels")

    def __init__(self, values, cutpoints, labels):
        self.values = np.asarray(values, dtype=float).reshape(-1)
        self.cutpoints = np.asarray(cutpoints, dtype=float)
        self.labels = list(labels)

    def __len__(self) -> int:
        return int(self.values.size)

    def __getitem__(self, key):
        subset = self.values[key]
        if isinstance(subset, np.ndarray) and subset.ndim == 0:
            subset = subset.reshape(1)
        elif not isinstance(subset, np.ndarray):
            subset = np.asarray([subset], dtype=float)
        return Tcut(subset, self.cutpoints, self.labels)


def levels(x: Tcut) -> list[str]:
    """Return category labels (``levels.tcut``)."""
    return list(x.labels)


def tcut(x, breaks, labels=None, scale=1):
    """Attach cutpoint categories without losing the underlying numeric values."""
    values = np.asarray(x, dtype=float).reshape(-1)
    breaks = np.atleast_1d(np.asarray(breaks, dtype=float))

    if breaks.size == 1:
        nb = int(breaks.item())
        if nb < 1:
            raise ValueError("Must specify at least one interval")
        finite = values[np.isfinite(values)]
        if finite.size:
            r0, r1 = float(np.min(finite)), float(np.max(finite))
        else:
            r0, r1 = 1.0, 1.0
        if r1 == r0:
            r1 = r0 + 1.0
        d = r1 - r0
        breaks = np.linspace(r0 - 0.01 * d, r1 + 0.01 * d, nb + 1)
        if labels is None:
            labels = [f"Range {i + 1}" for i in range(nb)]
        elif len(labels) != nb:
            raise ValueError("Number of labels must equal number of intervals")
    else:
        if np.any(np.diff(breaks) < 0) or np.any(np.isnan(breaks)):
            raise ValueError("breaks must be given in ascending order and contain no NA's")
        if labels is None:
            left = format_real(breaks[:-1].tolist())
            right = format_real(breaks[1:].tolist())
            labels = [f"{a}+ thru {b}" for a, b in zip(left, right)]
        elif len(labels) != breaks.size - 1:
            raise ValueError("Number of labels must be 1 less than number of break points")

    sc = float(scale)
    return Tcut(values * sc, breaks * sc, labels)
