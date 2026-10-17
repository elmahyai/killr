"""Silhouette widths, from ``src/sildist.c``, and the ordered silhouette."""

from __future__ import annotations

import math

import numpy as np


def _dist_vector(dist):
    values = np.asarray(dist, dtype=float)
    if values.ndim == 2:
        raise ValueError("pass a square matrix as dmatrix")
    return [float(v) for v in values.reshape(-1)]


def silhouette(x, dist=None, dmatrix=None):
    """Silhouette of an integer clustering.

    ``dist`` is a dissimilarity in dist order. ``dmatrix`` is a square matrix.
    A partition object with ``silinfo`` returns those stored widths.
    """
    if isinstance(x, dict) and "silinfo" in x and x.get("silinfo") and dist is None and dmatrix is None:
        widths = x["silinfo"]["widths"]
        return {
            "widths": widths,
            "ordered": True,
            "index": list(x["silinfo"].get("index") or []),
        }
    if isinstance(x, dict) and "clustering" in x and dist is None and dmatrix is None:
        x = x["clustering"]
    labels = [int(v) for v in np.asarray(x).reshape(-1)]
    n = len(labels)
    if any(v != round(v) for v in labels):
        raise ValueError("'x' must only have integer codes")
    unique = []
    for label in labels:
        if label not in unique:
            unique.append(label)
    k = len(unique)
    if k <= 1 or k >= n:
        return float("nan")
    recode = any(label < 1 or label > k for label in unique)
    if recode:
        ordered = sorted(set(labels))
        code = {label: i + 1 for i, label in enumerate(ordered)}
        coded = [code[label] for label in labels]
        back = ordered
    else:
        coded = labels
        back = None
    if dmatrix is not None:
        matrix = np.asarray(dmatrix, dtype=float)
        if matrix.shape != (n, n):
            raise ValueError("'dmatrix' is not a dissimilarity matrix compatible to 'x'")
        si, neighbor = _sildist_matrix(matrix, coded, k)
    else:
        if dist is None:
            raise ValueError("Need either a dissimilarity 'dist' or diss.matrix 'dmatrix'")
        vector = _dist_vector(dist)
        if len(vector) != n * (n - 1) // 2:
            raise ValueError("clustering 'x' and dissimilarity 'dist' are incompatible")
        si, neighbor = _sildist_vector(vector, coded, k)
    if recode:
        labels = [back[code - 1] for code in coded]
        neighbor = [back[code - 1] for code in neighbor]
    widths = [[float(labels[i]), float(neighbor[i]), float(si[i])] for i in range(n)]
    return {"widths": widths, "ordered": False, "codes": back}


def _sildist_vector(dist, clustering, k):
    n = len(clustering)
    counts = [0] * k
    di_c = [0.0] * (n * k)
    cursor = 0
    for i in range(n):
        ci = clustering[i] - 1
        counts[ci] += 1
        for j in range(i + 1, n):
            cj = clustering[j] - 1
            value = dist[cursor]
            cursor += 1
            di_c[k * i + cj] += value
            di_c[k * j + ci] += value
    return _finish(di_c, counts, clustering, k)


def _sildist_matrix(matrix, clustering, k):
    n = len(clustering)
    counts = [0] * k
    di_c = [0.0] * (n * k)
    # Column-major storage, reading d(j, i) for j > i.
    flat = np.asarray(matrix, dtype=float, order="F").reshape(-1)
    for i in range(n):
        ci = clustering[i] - 1
        counts[ci] += 1
        cursor = n * i + i + 1
        for j in range(i + 1, n):
            cj = clustering[j] - 1
            value = float(flat[cursor])
            cursor += 1
            di_c[k * i + cj] += value
            di_c[k * j + ci] += value
    return _finish(di_c, counts, clustering, k)


def _finish(di_c, counts, clustering, k):
    n = len(clustering)
    si = [0.0] * n
    neighbor = [0] * n
    for i in range(n):
        base = k * i
        ci = clustering[i] - 1
        compute = True
        for j in range(k):
            if j == ci:
                if counts[j] == 1:
                    compute = False
                else:
                    di_c[base + j] /= counts[j] - 1
            else:
                di_c[base + j] /= counts[j]
        ai = di_c[base + ci]
        if ci == 0:
            bi = di_c[base + 1]
            neighbor[i] = 2
        else:
            bi = di_c[base]
            neighbor[i] = 1
        for j in range(1, k):
            if j != ci and bi > di_c[base + j]:
                bi = di_c[base + j]
                neighbor[i] = j + 1
        if compute and bi != ai:
            si[i] = (bi - ai) / max(ai, bi)
        else:
            si[i] = 0.0
    return si, neighbor


def sort_silhouette(object):
    """Order a silhouette by cluster, then by decreasing width."""
    if isinstance(object, dict):
        widths = object["widths"]
        ordered = object.get("ordered", False)
        extra = {key: object[key] for key in object if key not in {"widths", "ordered", "i_ord"}}
    else:
        widths = object
        ordered = False
        extra = {}
    n = len(widths)
    if n < 1:
        raise ValueError("invalid silhouette structure")
    if ordered:
        result = {"widths": widths, "ordered": True, "i_ord": list(range(1, n + 1))}
        result.update(extra)
        return result
    indexed = list(enumerate(widths, start=1))
    indexed.sort(key=lambda item: (item[1][0], -item[1][2]))
    result = {
        "widths": [row for _index, row in indexed],
        "ordered": True,
        "i_ord": [index for index, _row in indexed],
    }
    result.update(extra)
    return result
