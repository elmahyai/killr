"""Combine Gaussian mixture components for clustering."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

__all__ = ["clust_combi"]


def clust_combi(object=None, data=None, **kwargs):
    """Hierarchy of combined clusterings from an EM/BIC Gaussian mixture."""
    if object is None and data is None:
        raise ValueError(
            "An object or class 'Mclust' or data as matrix/data.frame must be provided!"
        )
    if object is None:
        raise NotImplementedError(
            "clust_combi(data=...) requires Mclust, which is not translated yet"
        )
    if not _is_mclust(object):
        raise ValueError("object not of class 'Mclust'")
    if data is None:
        data = object["data"]
    return _combi(np.asarray(data, dtype=float), object)


def _is_mclust(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "G" in obj and "z" in obj and "data" in obj
    return hasattr(obj, "G") and hasattr(obj, "z") and hasattr(obj, "data")


def _mclust_field(obj: Any, name: str):
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _combi(data: np.ndarray, mclust_output: Any):
    g = int(_mclust_field(mclust_output, "G"))
    z = np.asarray(_mclust_field(mclust_output, "z"), dtype=float)
    if z.ndim == 1:
        z = z.reshape(-1, 1)

    combi_m: dict[int, np.ndarray] = {}
    combi_m[g] = np.eye(g, dtype=float)
    tau: dict[int, np.ndarray] = {}
    tau[g] = z.copy()
    classif: dict[int, np.ndarray] = {}
    classif[g] = _map(tau[g])

    for k in range(g, 1, -1):
        pre_combi_tau = tau[k]
        d_ent = np.zeros((k - 1, k), dtype=float)
        for l1 in range(1, k):
            for l2 in range(l1 + 1, k + 1):
                post_combi_tau = (_comb_mat(k, l1, l2) @ pre_combi_tau.T).T
                d_ent[l1 - 1, l2 - 1] = np.sum(_xlog(post_combi_tau[:, l1 - 1])) - (
                    np.sum(_xlog(pre_combi_tau[:, l1 - 1]))
                    + np.sum(_xlog(pre_combi_tau[:, l2 - 1]))
                )
        flat = d_ent.ravel(order="F")
        max_val = flat.max()
        first = int(np.flatnonzero(flat == max_val)[0])
        l1, l2 = np.unravel_index(first, d_ent.shape, order="F")
        l1 += 1
        l2 += 1

        combi_m[k - 1] = _comb_mat(k, l1, l2)
        tau[k - 1] = (combi_m[k - 1] @ pre_combi_tau.T).T
        classif[k - 1] = _map(tau[k - 1])

    return ClustCombiResult(
        classification=classif,
        combiM=combi_m,
        combiz=tau,
        MclustOutput=mclust_output,
    )


def _comb_mat(k: int, l1: int, l2: int) -> np.ndarray:
    lo, hi = (min(l1, l2), max(l1, l2))
    if l1 == 0 or l2 == 0:
        l1 = 0
        l2 = hi
    else:
        l1 = lo
        l2 = hi

    top_left = np.eye(l2 - 1)
    top_right = np.zeros((l2 - 1, k - l2 + 1))
    bottom_left = np.zeros((k - l2, l2))
    bottom_right = np.eye(k - l2)
    m = np.vstack(
        [np.hstack([top_left, top_right]), np.hstack([bottom_left, bottom_right])]
    )
    if l1 > 0:
        m[l1 - 1, l2 - 1] = 1.0
    return m


def _xlog(x: np.ndarray) -> np.ndarray:
    flat = np.asarray(x, dtype=float).ravel()
    out = np.where(flat == 0.0, 0.0, flat * np.log(flat))
    return out.reshape(x.shape)


def _map(z: np.ndarray, warn: bool = False) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    n_rows = z.shape[0]
    cl = np.empty(n_rows, dtype=float)
    for i in range(n_rows):
        row_max = z[i, :].max()
        cols = np.flatnonzero(z[i, :] == row_max)
        cl[i] = cols[0] + 1
    if warn:
        j = np.arange(1, z.shape[1] + 1)
        k = np.isin(j, np.unique(cl.astype(int)))
        if np.any(~k):
            missing = ",".join(str(int(v)) for v in j[~k])
            import warnings

            warnings.warn(f"no assignment to {missing}", stacklevel=2)
    return cl


class ClustCombiResult(dict):
    """Output of ``clustCombi``."""

    def __init__(
        self,
        *,
        classification: Mapping[int, np.ndarray],
        combiM: Mapping[int, np.ndarray],
        combiz: Mapping[int, np.ndarray],
        MclustOutput: Any,
    ):
        super().__init__(
            classification=dict(classification),
            combiM=dict(combiM),
            combiz=dict(combiz),
            MclustOutput=MclustOutput,
        )
