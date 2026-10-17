"""Projection parameters for ``MclustDR`` objects (``projpar.MclustDR``)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

__all__ = ["projpar_MclustDR"]


def projpar_MclustDR(
    object: Any,
    dim: Sequence[int] | None = None,
    *,
    center: bool = True,
    raw: bool = False,
) -> dict[str, np.ndarray]:
    """Transform mixture parameters into the ``dim`` projection subspace."""
    if not _is_mclust_dr(object):
        raise ValueError("object must be of class 'MclustDR'")

    x = np.asarray(_field(object, "x"), dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    p = x.shape[1]
    g = int(_field(object, "G"))
    object_numdir = int(_field(object, "numdir"))

    if dim is None:
        dim_idx = np.arange(1, object_numdir + 1, dtype=int)
    else:
        dim_idx = np.asarray(dim, dtype=int).ravel()
    numdir = int(dim_idx.size)
    cols = dim_idx - 1

    if raw:
        basis = np.asarray(_field(object, "raw.evectors"), dtype=float)
    else:
        basis = np.asarray(_field(object, "basis"), dtype=float)
    v = np.asarray(basis[:, cols], dtype=float)

    mu = np.asarray(_field(object, "mu"), dtype=float)
    if mu.shape[0] == p and mu.shape[1] == g:
        mu = mu.T
    elif not (mu.shape[0] == g and mu.shape[1] == p):
        raise ValueError("mu must be p x G or G x p")

    if center:
        mu = mu - x.mean(axis=0)

    mu_proj = mu @ v

    sigma = np.asarray(_field(object, "sigma"), dtype=float)
    if sigma.shape != (p, p, g):
        sigma = sigma.reshape(p, p, g, order="F")

    proj_sigma = np.empty((numdir, numdir, g), dtype=float)
    for j in range(g):
        r_upper = _chol_upper(sigma[:, :, j])
        rv = r_upper @ v
        proj_sigma[:, :, j] = rv.T @ rv

    return {"mean": np.asarray(mu_proj, dtype=float), "variance": proj_sigma}


def _is_mclust_dr(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "numdir" in obj and "basis" in obj and "mu" in obj and "sigma" in obj and "x" in obj
    return (
        hasattr(obj, "numdir")
        and hasattr(obj, "basis")
        and hasattr(obj, "mu")
        and hasattr(obj, "sigma")
        and hasattr(obj, "x")
    )


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _chol_upper(matrix: np.ndarray) -> np.ndarray:
    lower = np.linalg.cholesky(np.asarray(matrix, dtype=float))
    return lower.T
