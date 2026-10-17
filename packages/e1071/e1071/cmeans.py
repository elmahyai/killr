"""Fuzzy c-means clustering (e1071 ``cmeans``)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

_DIST = ("euclidean", "manhattan")
_METHOD = ("cmeans", "ufcl")


def _cmeans_ext():
    try:
        from cmeans import cmeans as impl
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "cmeans"))
        from cmeans import cmeans as impl
    return impl


def _boot_rng():
    try:
        from boot.rng import sample_int, set_seed
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int, set_seed
    return sample_int, set_seed


def _pmatch(value, choices):
    if value is None:
        return None
    text = str(value)
    hits = [index for index, choice in enumerate(choices) if choice.startswith(text)]
    if not hits:
        return None
    if len(hits) > 1:
        return -1
    return hits[0] + 1


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return np.asfortranarray(array)


def _unique_rows(matrix):
    _, index = np.unique(matrix, axis=0, return_index=True)
    return matrix[np.sort(index)]


def _duplicated_rows(matrix):
    seen = set()
    flags = []
    for row in matrix:
        key = tuple(float(value) for value in row)
        flags.append(key in seen)
        seen.add(key)
    return np.asarray(flags, dtype=bool)


def cmeans(
    x,
    centers,
    iter_max=100,
    verbose=False,
    dist="euclidean",
    method="cmeans",
    m=2,
    rate_par=None,
    weights=1,
    control=None,
):
    """Run fuzzy c-means or UFCL on a data matrix."""
    del verbose  # R prints when verbose; no Python console hook yet.
    matrix = _as_matrix(x)
    xrows, xcols = matrix.shape

    dist_code = _pmatch(dist, _DIST)
    if dist_code is None:
        raise ValueError("invalid distance")
    if dist_code == -1:
        raise ValueError("ambiguous distance")

    method_code = _pmatch(method, _METHOD)
    if method_code is None:
        raise ValueError("invalid clustering method")
    if method_code == -1:
        raise ValueError("ambiguous clustering method")

    sample_int, _ = _boot_rng()

    if centers is None:
        raise ValueError("Argument 'centers' must be a number or a matrix.")

    if np.isscalar(centers) or (isinstance(centers, (list, tuple)) and len(centers) == 1):
        ncenters = int(np.asarray(centers).reshape(-1)[0])
        picks = sample_int(xrows, ncenters, replace=False)
        center_matrix = matrix[np.asarray(picks, dtype=int) - 1, :]
        if np.any(_duplicated_rows(center_matrix)):
            unique_rows = _unique_rows(matrix)
            mm = unique_rows.shape[0]
            if mm < ncenters:
                raise ValueError("More cluster centers than distinct data points.")
            picks = sample_int(mm, ncenters, replace=False)
            center_matrix = unique_rows[np.asarray(picks, dtype=int) - 1, :]
    else:
        center_matrix = _as_matrix(centers)
        if np.any(_duplicated_rows(center_matrix)):
            raise ValueError("Initial centers are not distinct.")
        ncenters = center_matrix.shape[0]
        if xrows < ncenters:
            raise ValueError("More cluster centers than data points.")

    if xcols != center_matrix.shape[1]:
        raise ValueError("Must have same number of columns in 'x' and 'centers'.")

    if iter_max < 1:
        raise ValueError("Argument 'iter.max' must be positive.")

    if method_code == 2 and rate_par is None:
        rate_par = 0.3

    control = {} if control is None else dict(control)
    reltol = control.get("reltol")
    if reltol is None:
        reltol = math.sqrt(float(np.finfo(float).eps))
    if reltol <= 0:
        raise ValueError("Control parameter 'reltol' must be positive.")

    weights = np.asarray(weights, dtype=float)
    if np.any(weights < 0):
        raise ValueError("Argument 'weights' has negative elements.")
    if not np.any(weights > 0):
        raise ValueError("Argument 'weights' has no positive elements.")
    weights = np.resize(weights, xrows).astype(float, copy=False)
    weights = weights / np.sum(weights)

    perm = np.asarray(sample_int(xrows), dtype=int) - 1
    matrix = matrix[perm, :]
    weights = weights[perm]

    center_flat = np.asfortranarray(center_matrix.copy()).reshape(-1, order="F")
    x_flat = matrix.reshape(-1, order="F")

    kernel = _cmeans_ext()
    centers_out, membership, withinerror, raw_iter = kernel(
        x_flat,
        center_flat,
        weights,
        m=float(m),
        dist=dist_code - 1,
        iter_max=int(iter_max),
        reltol=float(reltol),
        ufcl=method_code == 2,
        rate_par=float(rate_par if rate_par is not None else 0.3),
    )

    centers_final = np.asarray(centers_out, dtype=float).reshape(ncenters, xcols, order="F")
    membership = np.asarray(membership, dtype=float).reshape(xrows, ncenters, order="F")
    inv_perm = np.empty_like(perm)
    inv_perm[perm] = np.arange(xrows)
    membership = membership[inv_perm, :]

    cluster = np.argmax(membership, axis=1) + 1
    size = np.bincount(cluster - 1, minlength=ncenters).astype(int)

    return {
        "centers": centers_final,
        "size": size,
        "cluster": cluster,
        "membership": membership,
        "iter": int(raw_iter) - 1,
        "withinerror": float(withinerror),
    }
