"""Convert hierarchical merge pairs into cluster classifications."""

from __future__ import annotations

import numpy as np

from mclust.model_metadata import partconv


def hclass(hcPairs, G=None):
    """Return classifications at the requested numbers of clusters.

    ``hcPairs`` is the two-row merge matrix returned by hierarchical
    clustering.  As in mclust, observations initially form singleton
    clusters numbered from one.
    """
    pairs = np.asarray(hcPairs)
    if pairs.ndim != 2 or pairs.shape[0] != 2:
        raise ValueError("hcPairs must be a two-row matrix")
    initial = getattr(hcPairs, "initialPartition", None)
    if initial is None:
        n = int(np.max(pairs)) if pairs.size else 1
        initial = np.arange(1, n + 1, dtype=int)
    else:
        initial = np.asarray(initial, dtype=int).reshape(-1)
        n = initial.size
    k = int(np.unique(initial).size)
    if G is None:
        groups = np.arange(k, 1, -1, dtype=int)
    else:
        groups = np.unique(np.asarray(G, dtype=int))[::-1]
    select = k - groups
    good = (select >= 0) & (select < k)
    if not np.any(good):
        raise ValueError("no classification with the specified number of clusters")
    groups = groups[good]
    select = select[good]

    if select.size == 1 and select[0] == 0:
        return initial[:, None]

    classifications = np.full((n, select.size), np.nan)
    current = initial.copy()
    if select[0] == 0:
        classifications[:, 0] = current

    for level in range(1, int(np.max(select)) + 1):
        i, j = sorted((int(pairs[0, level - 1]), int(pairs[1, level - 1])))
        current[current == j] = i
        matches = np.flatnonzero(select == level)
        for column in matches:
            classifications[:, column] = current

    # mclust presents the requested classifications in the reverse of the
    # merge traversal, then makes labels consecutive.
    result = np.empty_like(classifications, dtype=int)
    for column, source in enumerate(range(classifications.shape[1] - 1, -1, -1)):
        result[:, column] = partconv(classifications[:, source], consec=True)
    return result


__all__ = ["hclass"]
