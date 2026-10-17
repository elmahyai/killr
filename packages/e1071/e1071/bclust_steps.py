"""Hierarchical step of bagged clustering (e1071 ``hclust.bclust``, ``centers.bclust``, ``clusters.bclust``).

The distances come from ``proxy.dist``. The hierarchy is ``cluster.agnes`` or ``cluster.diana`` on
that distance, because the repository has no Python ``stats::hclust``. ``agnes`` covers the
``average``, ``single``, and ``complete`` linkages. ``cutree`` and the knn1 step use the translated
``e1071._cutree`` and ``class.knn1``. ``docmdscale = TRUE`` stores a native
classical multidimensional scaling of the distance object.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import numpy as np

from e1071._cutree import cutree
from e1071._kmns import kmeans_hartigan_wong

_AGNES_METHODS = ("average", "single", "complete")
_STATS_HCLUST_ONLY = ("ward.D", "ward.D2", "centroid", "median", "mcquitty")


def _package(top: str, module: str | None = None):
    """Import ``module`` (default ``top``) from the sibling package ``packages/<top>``."""
    root = str(Path(__file__).resolve().parents[2] / top)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(module or top)


def _rows(matrix) -> list[list[float]]:
    return [[float(value) for value in row] for row in np.asarray(matrix, dtype=float)]


def _as_matrix(x) -> np.ndarray:
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return array


def _members_column(object: dict[str, Any], k: int) -> np.ndarray:
    """R ``object$members[, k - 1]``. Column ``k - 1`` holds the cut into ``k`` groups."""
    members = np.asarray(object["members"], dtype=int)
    if members.ndim != 2 or k < 2 or k - 1 > members.shape[1]:
        raise IndexError("subscript out of bounds")
    return members[:, k - 2]


def _hclust_from_dist(dist_values, hclust_method: str) -> dict[str, Any]:
    if hclust_method == "diana":
        twins = _package("cluster").diana(list(dist_values), diss=True)
    elif hclust_method in _AGNES_METHODS:
        twins = _package("cluster").agnes(list(dist_values), diss=True, method=hclust_method)
    elif hclust_method in _STATS_HCLUST_ONLY:
        raise NotImplementedError(
            f"hclust.method '{hclust_method}' needs stats::hclust, which is not translated"
        )
    else:
        raise ValueError(f"unsupported hclust.method '{hclust_method}'")
    return _package("cluster", "cluster.twins").as_hclust(twins)


def _cmdscale(dist_values, k: int = 2) -> np.ndarray:
    """Classical scaling matching ``stats::cmdscale`` for a distance object."""
    n = int(getattr(dist_values, "size", 0))
    values = np.asarray(dist_values, dtype=float).reshape(-1)
    distances = np.zeros((n, n), dtype=float)
    index = 0
    for row in range(n):
        for col in range(row + 1, n):
            distances[row, col] = distances[col, row] = values[index]
            index += 1
    squared = distances * distances
    centered = squared - squared.mean(axis=1, keepdims=True)
    centered -= squared.mean(axis=0, keepdims=True)
    centered += squared.mean()
    eigenvalues, eigenvectors = np.linalg.eigh(-centered / 2.0)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    positive = np.maximum(eigenvalues[:k], 0.0)
    points = eigenvectors[:, :k].copy()
    for column in range(points.shape[1]):
        nonzero = np.flatnonzero(np.abs(points[:, column]) > 0)
        if nonzero.size and points[nonzero[-1], column] < 0:
            points[:, column] *= -1.0
    return points * np.sqrt(positive)


def hclust_bclust(
    object: dict[str, Any],
    x,
    centers: int,
    dist_method: str | None = None,
    hclust_method: str | None = None,
    final_kmeans: bool = False,
    docmdscale: bool = False,
    maxcluster: int | None = None,
) -> dict[str, Any]:
    """R ``hclust.bclust``. Returns a modified copy of the bclust object."""
    out = dict(object)
    dist_method = out["dist.method"] if dist_method is None else dist_method
    hclust_method = out["hclust.method"] if hclust_method is None else hclust_method
    maxcluster = out["maxcluster"] if maxcluster is None else maxcluster
    proxy_dist = _package("proxy").dist
    d = proxy_dist(_rows(out["allcenters"]), method=dist_method)
    if docmdscale:
        out["cmdscale"] = _cmdscale(d)
    out["hclust"] = _hclust_from_dist(d, hclust_method)

    k_values = list(range(2, int(maxcluster) + 1))
    if not k_values:
        raise ValueError("maxcluster must be at least 2")
    parts = cutree(out["hclust"]["merge"], k_values)
    out["members"] = np.asarray(parts, dtype=int).T

    out["cluster"] = clusters_bclust(out, int(centers))
    out["centers"] = centers_bclust(out, int(centers))
    if final_kmeans:
        fit = kmeans_hartigan_wong(_rows(_as_matrix(x)), out["centers"].tolist())
        out["centers"] = np.asarray(fit["centers"], dtype=float)
        out["cluster"] = np.asarray(fit["cluster"], dtype=int)
    return out


def centers_bclust(object: dict[str, Any], k: int) -> np.ndarray:
    """R ``centers.bclust``. Row ``m`` is the mean of the base centers in group ``m``.

    An empty group gives NaN, as R's ``apply(..., mean)`` does.
    """
    allcenters = np.asarray(object["allcenters"], dtype=float)
    members = _members_column(object, k)
    centers = np.empty((k, allcenters.shape[1]), dtype=float)
    for m in range(1, k + 1):
        group = allcenters[members == m]
        if group.shape[0] == 0:
            centers[m - 1, :] = np.nan
        else:
            centers[m - 1, :] = group.mean(axis=0)
    return centers


def clusters_bclust(object: dict[str, Any], k: int, x=None) -> np.ndarray:
    """R ``clusters.bclust``. With ``x=None`` (R: missing), uses the stored ``allcluster``."""
    if x is None:
        allcluster = np.asarray(object["allcluster"], dtype=int)
    else:
        knn1 = _package("class", "class.knn").knn1
        train = _rows(object["allcenters"])
        labels = [str(i + 1) for i in range(len(train))]
        allcluster = np.asarray([int(v) for v in knn1(train, _rows(_as_matrix(x)), labels)], dtype=int)
    members = _members_column(object, k)
    return members[allcluster - 1]
