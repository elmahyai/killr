"""Random-pairs hierarchical clustering initialization."""

from __future__ import annotations

import numpy as np

from mclust.utility_functions import randomPairs


class _HCPairs(np.ndarray):
    """Pair matrix carrying the metadata attached by mclust."""

    def __new__(cls, pairs, n):
        result = np.asarray(pairs, dtype=int).view(cls)
        result.initialPartition = np.arange(1, n + 1, dtype=int)
        result.dimensions = np.array([n, 2], dtype=int)
        return result

    def __array_finalize__(self, obj):
        if obj is not None:
            self.initialPartition = getattr(obj, "initialPartition", None)
            self.dimensions = getattr(obj, "dimensions", None)


def hcRandomPairs(data, seed=None, **kwargs):
    """Generate the random merge-pair tree used by hierarchical clustering."""
    x = np.asarray(data)
    if x.ndim == 0:
        raise ValueError("data must have rows")
    return _HCPairs(randomPairs(x, seed=seed), x.shape[0])


__all__ = ["hcRandomPairs"]
