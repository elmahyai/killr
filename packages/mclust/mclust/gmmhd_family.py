"""Gaussian-mixture high-density (GMMHD) helpers.

The fitting and classification entry points retain the dependency boundary of
the R package: the translated mclustBIC/MclustDA fitters are not available yet.
The object methods and cluster-core post-processing do not require those
fitters and are implemented here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

__all__ = [
    "gmmhd",
    "print_gmmhd",
    "summary_gmmhd",
    "print_summary_gmmhd",
    "gmmhdClusterCores",
    "gmmhdClassify",
]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def gmmhd(object: Any, ngrid: int | None = None, dr: Any = None,
          classify: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Fit a GMMHD object.

    The actual fit invokes ``Mclust`` through ``mclustBIC`` and, for the
    projection path, ``MclustDA``.  Those same-package routines are still
    untranslated, so silently substituting another estimator would change R's
    result.
    """
    del ngrid, dr, classify, kwargs
    if not _is_mclust(object):
        raise ValueError("first argument must be an object of class 'Mclust'")
    raise NotImplementedError("gmmhd is waiting on mclustBIC and MclustDA")


def gmmhdClusterCores(object: Any, tails: bool = False, **kwargs: Any) -> np.ndarray:
    """Extract the nested high-density connected-component cores."""
    del tails, kwargs
    x = np.asarray(_get(object, "x"), dtype=float)
    n = x.shape[0]
    nc = np.asarray(_get(object, "nc"), dtype=float).reshape(-1)
    con = _get(object, "con")
    if nc.size == 0 or con is None:
        return np.full(n, np.nan)
    drops = np.diff(np.r_[nc, 0.0]) < 0
    candidates = np.flatnonzero(drops)
    if candidates.size == 0:
        return np.full(n, np.nan)
    best = np.flatnonzero(nc == np.max(nc[candidates]))
    cores = np.full((n, best.size), np.nan)
    for j, idx in enumerate(best):
        for label, component in enumerate(con[int(idx)], 1):
            # R indices are one-based; accept either R-style indices or
            # Python-style indices when the object was built in Python.
            inds = np.asarray(component, dtype=int).reshape(-1)
            if inds.size and np.min(inds) >= 1:
                inds = inds - 1
            cores[inds, j] = label
    while cores.shape[1] > 1:
        labels = np.unique(cores[:, 1][~np.isnan(cores[:, 1])]).astype(int)
        tmp = np.empty(n, dtype=np.object_)
        tmp[:] = None
        for label in labels:
            rows = cores[:, 1] == label
            previous = cores[rows, 0]
            previous = previous[~np.isnan(previous)]
            if previous.size == 0 or np.unique(previous).size <= 1:
                value: Any = f"{label}*"
            else:
                value = previous
            tmp[rows] = value
        levels = sorted({str(v) for v in tmp if not pd_isna(v)})
        code = {level: i + 1 for i, level in enumerate(levels)}
        next_col = np.full(n, np.nan, dtype=float)
        for i, value in enumerate(tmp):
            if not pd_isna(value):
                next_col[i] = code[str(value)]
        cores = np.column_stack((next_col, cores[:, 2:]))
    return cores[:, 0]


def gmmhdClassify(object: Any, G: Any = None, modelNames: Any = None,
                  verbose: bool = True, **kwargs: Any) -> dict[str, Any]:
    """Classify non-core observations using MclustDA.

    ``MclustDA`` is a same-package translation still in progress.
    """
    del G, modelNames, verbose, kwargs
    if not _is_gmmhd(object):
        raise ValueError("object is not of class 'gmmhd'")
    raise NotImplementedError("gmmhdClassify is waiting on MclustDA")


def summary_gmmhd(object: Any, **kwargs: Any) -> dict[str, Any]:
    """Return the R ``summary.gmmhd`` representation."""
    del kwargs
    title = "GMM with high-density connected components for clustering"
    initial = _get(object, "Mclust")
    projection = _get(object, "MclustDR")
    out: dict[str, Any] = {
        "title": title,
        "Mclust": {"G": _get(initial, "G"), "modelName": _get(initial, "modelName")},
        "MclustDR": None if projection is None else {
            "G": _get(projection, "G"), "modelName": _get(projection, "modelName")
        },
        "clusterCores": _table(_get(object, "clusterCores")),
        "cluster": _table(_get(object, "cluster")),
    }
    return out


def print_gmmhd(x: Any, digits: int = 7, **kwargs: Any) -> Any:
    """Print a GMMHD object in R's compact format and return it."""
    del digits, kwargs
    print("'gmmhd' model object:")
    initial = _get(x, "Mclust")
    print(f" Mclust initial model = ({_get(initial, 'modelName')},{_get(initial, 'G')})")
    projection = _get(x, "MclustDR")
    if projection is not None:
        print(f" MclustDR projection = ({_get(projection, 'modelName')},{_get(projection, 'G')})")
    print(f" GMMHD final number of clusters = {_get(x, 'numClusters')}")
    return x


def print_summary_gmmhd(x: Mapping[str, Any], digits: int = 7, **kwargs: Any) -> Any:
    """Print a ``summary.gmmhd`` object and return it."""
    del digits, kwargs
    title = str(_get(x, "title"))
    print("-" * len(title), end=" \n")
    print(title)
    print("-" * len(title), end=" \n")
    initial = _get(x, "Mclust")
    print(f"\nInitial model:  Mclust ({_get(initial, 'modelName')},{_get(initial, 'G')})")
    projection = _get(x, "MclustDR")
    if projection is not None:
        print(f"\nModel on projection subspace:  ({_get(projection, 'modelName')},{_get(projection, 'G')})")
    print("\nCluster cores:")
    _print_table(_get(x, "clusterCores"))
    print("\nFinal clustering:")
    _print_table(_get(x, "cluster"))
    return x


def _table(values: Any) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float).reshape(-1)
    finite = arr[~np.isnan(arr)]
    labels, counts = np.unique(finite.astype(int), return_counts=True)
    return {"values": counts.astype(int), "names": labels.astype(int)}


def _print_table(tab: Any) -> None:
    values = np.asarray(_get(tab, "values", tab)).reshape(-1)
    names = _get(tab, "names")
    if names is None:
        names = np.arange(1, values.size + 1)
    print(" ".join(str(v) for v in names), end=" \n")
    print(" ".join(str(v) for v in values), end=" \n")


def _is_mclust(obj: Any) -> bool:
    return _get(obj, "data") is not None and _get(obj, "parameters") is not None and _get(obj, "modelName") is not None


def _is_gmmhd(obj: Any) -> bool:
    return _get(obj, "x") is not None and _get(obj, "con") is not None and _get(obj, "nc") is not None


def pd_isna(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False
