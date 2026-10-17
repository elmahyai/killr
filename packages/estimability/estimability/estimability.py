"""Tools for assessing estimability of linear predictions.

The public functions mirror the computational part of R's estimability
package.  Model-facing functions accept mappings or objects exposing
``design_matrix``, ``predict`` and (optionally) ``nonest``.
"""

from __future__ import annotations

from copy import copy
import time
from typing import Any

import numpy as np


ALL_ESTBLE = np.array([[np.nan]])
all_estble = ALL_ESTBLE


def _is_all_estble(nbasis: Any) -> bool:
    try:
        a = np.asarray(nbasis)
        return a.size > 0 and bool(np.isnan(a.flat[0]))
    except (TypeError, ValueError):
        return False


def _canonical_columns(a: np.ndarray) -> np.ndarray:
    """Choose a stable representative; each column's largest entry is +."""
    a = np.asarray(a, dtype=float).copy()
    if a.ndim == 2:
        for j in range(a.shape[1]):
            i = int(np.argmax(np.abs(a[:, j])))
            if a[i, j] < 0:
                a[:, j] *= -1
    return a


def nonest_basis_svd(
    x: Any, tol: float = 5e-8, rank: int | None = None,
    pivot: Any = None, **_: Any
) -> np.ndarray:
    """Return an orthonormal basis for the null space represented by an SVD.

    ``x`` may be a mapping with ``d`` and ``v`` (or ``vt``), or an object with
    attributes of those names.  ``v`` must be the complete right-singular
    vector matrix, as in ``R::svd(..., nv = ncol(x))``.
    """
    def get(name: str, default: Any = None) -> Any:
        if isinstance(x, dict):
            return x.get(name, default)
        return getattr(x, name, default)

    v = get("v")
    if v is None and get("vt") is not None:
        v = np.asarray(get("vt")).T
    d = np.asarray(get("d"), dtype=float).ravel()
    if v is None:
        raise ValueError("an SVD result with complete 'v' is required")
    v = np.asarray(v, dtype=float)
    if v.ndim != 2 or v.shape[1] < d.size:
        raise ValueError("the SVD right-singular vectors must be complete")
    if rank is None:
        if v.shape[1] > d.size:
            d = np.concatenate((d, np.zeros(v.shape[1] - d.size)))
        if d.size == 0:
            return ALL_ESTBLE.copy()
        keep = np.flatnonzero(d < d[0] * tol)
    else:
        keep = np.arange(int(rank), v.shape[1])
    if keep.size == 0:
        return ALL_ESTBLE.copy()
    bas = v[:, keep].copy()
    if pivot is not None:
        p = np.asarray(pivot, dtype=int).ravel()
        if p.size != bas.shape[0]:
            raise ValueError("pivot must have one entry per coefficient")
        if p.min(initial=0) >= 1:
            p = p - 1
        out = np.empty_like(bas)
        out[p, :] = bas
        bas = out
    return bas


def nonest_basis(x: Any, tol: float = 5e-8, rank: int | None = None,
                 pivot: Any = None, **kwargs: Any) -> np.ndarray:
    """Return a basis for the non-estimable coefficient directions."""
    if isinstance(x, dict) and ("d" in x or "v" in x or "vt" in x):
        return nonest_basis_svd(x, tol=tol, rank=rank, pivot=pivot, **kwargs)
    if hasattr(x, "d") or hasattr(x, "v") or hasattr(x, "vt"):
        return nonest_basis_svd(x, tol=tol, rank=rank, pivot=pivot, **kwargs)
    a = np.asarray(x, dtype=float)
    if a.ndim != 2:
        raise ValueError("x must be a matrix or an SVD result")
    _, d, vt = np.linalg.svd(a, full_matrices=True)
    return nonest_basis_svd(
        {"d": d, "v": vt.T}, tol=tol, rank=rank, pivot=pivot, **kwargs
    )


def legacy_nonest_basis(x: Any, **_: Any) -> np.ndarray:
    """Legacy QR-based null-space basis."""
    a = np.asarray(x, dtype=float)
    if a.ndim != 2:
        raise ValueError("legacy_nonest_basis requires a matrix")
    p = a.shape[1]
    q, r = np.linalg.qr(a, mode="reduced")
    rank = int(np.linalg.matrix_rank(a))
    rt = r.T
    if rt.shape[1] < p:
        rt = np.column_stack((rt, np.zeros((p, p - rt.shape[1]))))
    rt[rank:, rank:] += np.eye(p - rank)
    q2, _ = np.linalg.qr(rt, mode="complete")
    return ALL_ESTBLE.copy() if rank == p else q2[:, rank:]


def is_estble(x: Any, nbasis: Any, tol: float = 1e-8) -> Any:
    """Test whether vectors (rows of a matrix) are estimable."""
    a = np.asarray(x, dtype=float)
    if a.ndim == 2:
        return np.asarray([is_estble(row, nbasis, tol) for row in a], dtype=bool)
    if _is_all_estble(nbasis):
        return True
    v = np.nan_to_num(a, nan=0.0)
    n = np.asarray(nbasis, dtype=float)
    check = n.T @ v
    ssq = float(np.sum(v * v))
    if ssq < tol:
        ssq = 1.0
    return bool(float(np.sum(check * check)) < tol * ssq)


class EstimableSubspace(np.ndarray):
    """Array result from :func:`estble_subspace`, carrying R's ``B`` attr."""

    B: np.ndarray

    def __new__(cls, value: Any, B: np.ndarray):
        obj = np.asarray(value, dtype=float).view(cls)
        obj.B = B
        return obj


def estble_subspace(L: Any, nbasis: Any, tol: float = 1e-8) -> EstimableSubspace:
    """Restrict rows of ``L`` to its estimable subspace."""
    l = np.asarray(L, dtype=float)
    if np.all(is_estble(l, nbasis, tol)):
        b = np.eye(l.shape[0])
    else:
        ln = l @ np.asarray(nbasis, dtype=float)
        ln[np.abs(ln) <= tol] = 0.0
        b = nonest_basis(ln.T, tol=tol).T
    if _is_all_estble(b) or b.shape[0] == 0 or np.isnan(b.flat[0]):
        result = np.empty((0, l.shape[1]))
    else:
        result = b @ l
    return EstimableSubspace(result, b)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def epredict(object: Any, newdata: Any = None, *, type: str = "response",
             nonest_tol: float = 1e-8, nbasis: Any = None, **kwargs: Any) -> Any:
    """Predict while replacing non-estimable new-data rows with ``NaN``.

    The model supplies ``design_matrix(newdata)`` and ``predict(newdata, ...)``
    callables.  ``type='matrix'`` returns the design matrix and
    ``type='estimability'`` returns its row-wise mask.
    """
    if newdata is None:
        pred = _get(object, "predict")
        return pred(None, **kwargs) if callable(pred) else pred
    design = _get(object, "design_matrix")
    if not callable(design):
        raise TypeError("object must provide a design_matrix(newdata) callable")
    X = np.asarray(design(newdata), dtype=float)
    if nbasis is None:
        nbasis = _get(object, "nonest", None)
    if nbasis is None:
        nbasis = nonest_basis(X)
    mask = np.asarray(is_estble(X, nbasis, nonest_tol), dtype=bool)
    if type == "estimability":
        return mask
    if type == "matrix":
        return X
    pred = _get(object, "predict")
    if not callable(pred):
        raise TypeError("object must provide a predict(newdata, ...) callable")
    result = np.asarray(pred(newdata, type=type, **kwargs)).copy()
    result[~mask] = np.nan
    return result


def eupdate(object: Any, **kwargs: Any) -> Any:
    """Copy a model and attach its non-estimability basis."""
    obj = copy(object)
    if kwargs:
        updater = _get(obj, "update")
        if not callable(updater):
            raise TypeError("object must provide update(**kwargs) for eupdate options")
        obj = updater(**kwargs)
    design = _get(obj, "design_matrix")
    if not callable(design):
        raise TypeError("object must provide a design_matrix callable")
    X = np.asarray(design(None), dtype=float)
    basis = nonest_basis(X)
    if isinstance(obj, dict):
        obj["nonest"] = basis
    else:
        setattr(obj, "nonest", basis)
    return obj


__all__ = [
    "ALL_ESTBLE", "all_estble", "epredict", "estble_subspace", "eupdate",
    "is_estble", "legacy_nonest_basis", "nonest_basis", "nonest_basis_svd",
]
