"""Fuzzy cluster validity indexes (e1071 ``fclustIndex``)."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence, Union

import numpy as np

_INDEX_CHOICES = (
    "gath.geva",
    "xie.beni",
    "fukuyama.sugeno",
    "partition.coefficient",
    "partition.entropy",
    "proportion.exponent",
    "separation.index",
    "all",
)

_INDEX_NAMES = ("fhv", "apd", "pd", "xb", "fs", "pc", "pe", "pre", "si")


def _pmatch(value: Any, choices: Sequence[str]) -> int | None:
    if value is None:
        return None
    text = str(value)
    hits = [index for index, choice in enumerate(choices) if choice.startswith(text)]
    if not hits:
        return None
    if len(hits) > 1:
        return -1
    return hits[0] + 1


def _as_matrix(x) -> np.ndarray:
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return np.asfortranarray(array)


def _cluster_result(y: Mapping[str, Any]) -> dict[str, np.ndarray | float | int]:
    membership = np.asfortranarray(np.asarray(y["membership"], dtype=float))
    centers = np.asfortranarray(np.asarray(y["centers"], dtype=float))
    withinerror = float(y["withinerror"])
    cluster = np.asarray(y["cluster"], dtype=int)
    return {
        "membership": membership,
        "centers": centers,
        "withinerror": withinerror,
        "cluster": cluster,
    }


def _gath_geva(clres: dict[str, Any], x: np.ndarray) -> tuple[float, float, float]:
    membership = clres["membership"]
    centers = clres["centers"]
    xrows, xcols = membership.shape[0], centers.shape[1]
    ncenters = centers.shape[0]
    scatter = np.zeros((xcols, xcols, ncenters), dtype=float)
    fhv = 0.0
    apd = 0.0
    pd_sum = 0.0

    for i in range(ncenters):
        paronomastis = 0.0
        paronomastis2 = 0.0
        for j in range(xrows):
            weight = float(membership[j, i])
            paronomastis += weight
            diff = x[j, :] - centers[i, :]
            scatter[:, :, i] += weight * np.outer(diff, diff)
        scatter[:, :, i] /= paronomastis

        inv_scatter = np.linalg.inv(scatter[:, :, i])
        for j in range(xrows):
            diff = x[j, :] - centers[i, :]
            control = float(diff @ inv_scatter @ diff)
            if control < 1.0:
                paronomastis2 += float(membership[j, i])

        det_scatter = float(np.linalg.det(scatter[:, :, i]))
        root_det = math.sqrt(det_scatter)
        fhv += root_det
        apd += paronomastis2 / root_det
        pd_sum += paronomastis2

    pd = pd_sum / fhv
    apd /= ncenters
    return fhv, apd, pd


def _xie_beni(clres: dict[str, Any]) -> float:
    membership = clres["membership"]
    centers = clres["centers"]
    xrows = membership.shape[0]
    error = float(clres["withinerror"])
    ncenters = centers.shape[0]
    minimum = -1.0
    for i in range(ncenters - 1):
        for j in range(i + 1, ncenters):
            diff = centers[i, :] - centers[j, :]
            diffdist = float(diff @ diff)
            if minimum == -1.0:
                minimum = diffdist
            elif diffdist < minimum:
                minimum = diffdist
    return error / (xrows * minimum)


def _fukuyama_sugeno(clres: dict[str, Any]) -> float:
    membership = clres["membership"]
    centers = clres["centers"]
    xrows, ncenters = membership.shape
    error = float(clres["withinerror"])
    meancenters = np.mean(centers, axis=0)
    k2 = 0.0
    for i in range(ncenters):
        paronomastis3 = float(np.sum(membership[:, i] ** 2))
        diff = centers[i, :] - meancenters
        diffdist = float(diff @ diff)
        k2 += paronomastis3 * diffdist
    return error - k2


def _partition_coefficient(clres: dict[str, Any]) -> float:
    membership = clres["membership"]
    xrows = membership.shape[0]
    return float(np.sum(np.sum(membership**2, axis=1)) / xrows)


def _partition_entropy(clres: dict[str, Any]) -> float:
    membership = clres["membership"]
    xrows, ncenters = membership.shape
    partitionentropy = 0.0
    for i in range(xrows):
        for k in range(ncenters):
            value = float(membership[i, k])
            if value != 0.0:
                partitionentropy += value * math.log(value)
    return partitionentropy / ((-1) * xrows)


def _proportion_exponent(clres: dict[str, Any]) -> float:
    centers = clres["centers"]
    membership = clres["membership"]
    k = centers.shape[1]
    xrows = membership.shape[0]
    bexp = 1
    for j in range(xrows):
        row_max = float(np.max(membership[j, :]))
        greatint = int(1 / row_max)
        aexp = 0.0
        for l in range(1, greatint + 1):
            aexp += ((-1) ** (l + 1)) * (
                math.gamma(k + 1) / (math.gamma(l + 1) * math.gamma(k - l + 1))
            ) * (1 - l * row_max) ** (k - 1)
        bexp *= aexp
    return -math.log(bexp)


def _max_dist_rows(rows: np.ndarray) -> float:
    n = rows.shape[0]
    if n < 2:
        return float("-inf")
    maximum = -1.0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = rows[i, :] - rows[j, :]
            dist = math.sqrt(float(diff @ diff))
            if dist > maximum:
                maximum = dist
    return maximum


def _separation_index(clres: dict[str, Any], x: np.ndarray) -> float:
    cluster = clres["cluster"]
    xcols = x.shape[1]
    ncenters = clres["centers"].shape[0]
    maxcluster = np.zeros(ncenters, dtype=float)
    for i in range(ncenters):
        mask = cluster == (i + 1)
        maxcluster[i] = _max_dist_rows(x[mask, :])

    order = np.argsort(maxcluster)[::-1]
    maxdia = float(maxcluster[order[0]])

    minimum = -1.0
    for i in range(ncenters - 1):
        for j in range(i + 1, ncenters):
            for m in range(x.shape[0]):
                if cluster[m] != (i + 1):
                    continue
                for l in range(x.shape[0]):
                    if cluster[l] != (j + 1):
                        continue
                    diff = x[m, :] - x[l, :]
                    diffdist = math.sqrt(float(diff @ diff))
                    fraction = diffdist / maxdia
                    if minimum == -1.0:
                        minimum = fraction
                    elif fraction < minimum:
                        minimum = fraction
    return minimum


def fclust_index(
    y: Mapping[str, Any],
    x,
    index: Union[str, Sequence[str]] = "all",
) -> Union[float, dict[str, float], list[float]]:
    """Compute fuzzy clustering validity indexes for a ``cmeans`` result."""
    clres = _cluster_result(y)
    matrix = _as_matrix(x)
    if matrix.shape != (clres["membership"].shape[0], clres["centers"].shape[1]):
        raise ValueError("'x' must have the same number of rows as 'y$membership' and columns as 'y$centers'")

    if isinstance(index, (list, tuple)):
        index_codes = [_pmatch(item, _INDEX_CHOICES) for item in index]
    else:
        index_codes = [_pmatch(index, _INDEX_CHOICES)]

    if any(code is None for code in index_codes):
        raise ValueError("invalid clustering index")
    if any(code == -1 for code in index_codes):
        raise ValueError("ambiguous index")

    code_set = set(index_codes)
    single = len(index_codes) == 1
    index_code = index_codes[0] if single else None

    vecallindex = np.zeros(9, dtype=float)

    if 1 in code_set or 8 in code_set:
        fhv, apd, pd = _gath_geva(clres, matrix)
        vecallindex[0] = fhv
        vecallindex[1] = apd
        vecallindex[2] = pd
    if 2 in code_set or 8 in code_set:
        vecallindex[3] = _xie_beni(clres)
    if 3 in code_set or 8 in code_set:
        vecallindex[4] = _fukuyama_sugeno(clres)
    if 4 in code_set or 8 in code_set:
        vecallindex[5] = _partition_coefficient(clres)
    if 5 in code_set or 8 in code_set:
        vecallindex[6] = _partition_entropy(clres)
    if 6 in code_set or 8 in code_set:
        vecallindex[7] = _proportion_exponent(clres)
    if 7 in code_set or 8 in code_set:
        vecallindex[8] = _separation_index(clres, matrix)

    if not single:
        return {name: float(vecallindex[i]) for i, name in enumerate(_INDEX_NAMES)}

    assert index_code is not None
    if index_code == 8:
        return {name: float(vecallindex[i]) for i, name in enumerate(_INDEX_NAMES)}
    if index_code == 1:
        return [float(vecallindex[i]) for i in range(3)]
    return float(vecallindex[index_code + 2])
