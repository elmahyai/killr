"""Bagged clustering (e1071 ``bclust``)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

from e1071._cutree import cutree
from e1071._kmns import kmeans_hartigan_wong


def _class_knn1():
    import importlib

    root = Path(__file__).resolve().parents[2] / "class"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    pkg = importlib.import_module("class.knn")
    return pkg.knn1


def _cluster_twins():
    try:
        from cluster import agnes, diana
        from cluster.twins import as_hclust
    except ImportError:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "cluster"))
        from cluster import agnes, diana
        from cluster.twins import as_hclust
    return agnes, diana, as_hclust


def _boot_sample():
    try:
        from boot import rng
        from boot.censored import _weighted_index
    except ImportError:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "boot"))
        from boot import rng
        from boot.censored import _weighted_index
    return rng, _weighted_index


def _rows(matrix: np.ndarray) -> list[list[float]]:
    return [[float(value) for value in row] for row in np.asarray(matrix, dtype=float)]


def _as_matrix(x) -> np.ndarray:
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return np.asfortranarray(array)


def _complete_cases_rows(matrix: np.ndarray) -> np.ndarray:
    return matrix[~np.any(np.isnan(matrix), axis=1)]


def _resolve_base_method(name: str) -> Callable[..., dict]:
    text = str(name)
    if text == "kmeans" or text.startswith("kmeans"):
        return lambda data, centers, **kw: kmeans_hartigan_wong(data, centers, **kw)
    raise ValueError(f"unsupported base.method '{name}'")


def _prune_bclust(object: dict, x: np.ndarray, minsize: int) -> dict:
    knn1 = _class_knn1()
    train = _rows(object["allcenters"])
    while True:
        labels = [str(i + 1) for i in range(len(train))]
        object["allcluster"] = np.asarray(
            [int(label) for label in knn1(train, _rows(x), labels)],
            dtype=int,
        )
        counts = np.bincount(object["allcluster"], minlength=len(train) + 1)
        ok = counts[1:] >= minsize
        if np.all(ok):
            break
        object["allcenters"] = object["allcenters"][ok]
        train = _rows(object["allcenters"])
    return object


def _centers_bclust(object: dict, k: int) -> np.ndarray:
    allcenters = object["allcenters"]
    members = object["members"]
    p = allcenters.shape[1]
    out = np.zeros((k, p), dtype=float)
    col = members[:, k - 2]
    for m in range(1, k + 1):
        mask = col == m
        if np.any(mask):
            out[m - 1] = np.mean(allcenters[mask], axis=0)
    return out


def _clusters_bclust(object: dict, k: int, x: np.ndarray | None) -> np.ndarray:
    knn1 = _class_knn1()
    if x is None:
        allcluster = object["allcluster"]
    else:
        train = _rows(object["allcenters"])
        labels = [str(i + 1) for i in range(len(train))]
        allcluster = np.asarray([int(v) for v in knn1(train, _rows(x), labels)], dtype=int)
    return object["members"][allcluster - 1, k - 2]


def _hclust_bclust(
    object: dict,
    x: np.ndarray,
    centers: int,
    dist_method: str,
    hclust_method: str,
    final_kmeans: bool,
    docmdscale: bool,
    maxcluster: int,
) -> dict:
    agnes_fn, diana_fn, as_hclust = _cluster_twins()
    rows = _rows(object["allcenters"])
    metric = str(dist_method).lower()
    if hclust_method == "diana":
        twins = diana_fn(rows, diss=False, metric=metric)
        hclust = as_hclust(twins)
    else:
        twins = agnes_fn(rows, diss=False, metric=metric, method=hclust_method)
        hclust = as_hclust(twins)
    object["hclust"] = hclust
    if docmdscale:
        object["cmdscale"] = None  # not requested in proof
    k_values = list(range(2, maxcluster + 1))
    if k_values:
        parts = cutree(hclust["merge"], k_values)
        object["members"] = np.asarray(parts, dtype=int).T
    else:
        object["members"] = np.empty((len(rows), 0), dtype=int)
    object["cluster"] = _clusters_bclust(object, centers, x)
    object["centers"] = _centers_bclust(object, centers)
    if final_kmeans:
        fit = kmeans_hartigan_wong(_rows(x), object["centers"].tolist())
        object["centers"] = np.asarray(fit["centers"], dtype=float)
        object["cluster"] = np.asarray(fit["cluster"], dtype=int)
    return object


def bclust(
    x,
    centers: int = 2,
    iter_base: int = 10,
    minsize: int = 0,
    dist_method: str = "euclidean",
    hclust_method: str = "average",
    base_method: str = "kmeans",
    base_centers: int = 20,
    verbose: bool = True,
    final_kmeans: bool = False,
    docmdscale: bool = False,
    resample: bool = True,
    weights=None,
    maxcluster: int | None = None,
    **kwargs: Any,
):
    """Bagged clustering with hierarchical combination of base partitions."""
    if docmdscale:
        raise NotImplementedError("docmdscale=TRUE needs cmdscale, which is not translated")
    matrix = _as_matrix(x)
    xr, xc = matrix.shape
    if maxcluster is None:
        maxcluster = base_centers
    clusfun = _resolve_base_method(base_method)
    rng, weighted_index = _boot_sample()

    object: dict[str, Any] = {
        "allcenters": np.zeros((iter_base * base_centers, xc), dtype=float),
        "allcluster": None,
        "hclust": None,
        "members": None,
        "cluster": None,
        "centers": None,
        "iter.base": iter_base,
        "base.centers": base_centers,
        "prcomp": None,
        "datamean": np.mean(matrix, axis=0),
        "colnames": None,
        "dist.method": dist_method,
        "hclust.method": hclust_method,
        "maxcluster": maxcluster,
    }
    if hasattr(x, "columns"):
        object["colnames"] = list(x.columns)
    elif isinstance(x, np.ndarray) and x.dtype.names:
        object["colnames"] = list(x.dtype.names)

    if verbose:
        print("Committee Member:", end="")
    for n in range(1, iter_base + 1):
        if verbose:
            print(f" {n}", end="")
        if resample:
            if weights is None:
                picks = rng.sample_int(xr, xr, replace=True)
            else:
                picks = weighted_index(xr, xr, weights)
            x1 = matrix[np.asarray(picks, dtype=int) - 1, :]
        else:
            x1 = matrix
        tryres = None
        for m in range(1, 21):
            if verbose:
                print(f"({m})", end="")
            try:
                tryres = clusfun(_rows(x1), base_centers, **kwargs)
            except Exception:
                tryres = None
                continue
            break
        # R: if(m==20) stop(...), which also fires when the 20th try succeeds
        if m == 20:
            raise RuntimeError("Could not find valid cluster solution in 20 replications\n")
        start = (n - 1) * base_centers
        end = n * base_centers
        object["allcenters"][start:end, :] = np.asarray(tryres["centers"], dtype=float)
    if verbose:
        print("\nComputing Hierarchical Clustering")

    object["allcenters"] = _complete_cases_rows(object["allcenters"])
    knn1 = _class_knn1()
    train = _rows(object["allcenters"])
    labels = [str(i + 1) for i in range(len(train))]
    object["allcluster"] = np.asarray([int(v) for v in knn1(train, _rows(matrix), labels)], dtype=int)

    if minsize > 0:
        object = _prune_bclust(object, matrix, minsize)

    object = _hclust_bclust(
        object,
        matrix,
        int(centers),
        dist_method,
        hclust_method,
        final_kmeans,
        False,
        int(maxcluster),
    )
    return object
