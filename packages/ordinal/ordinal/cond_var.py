"""Conditional variances of random effects for clmm fits (ordinal condVar)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class CondVarFrame:
    """One grouping factor's conditional variances (R data.frame)."""

    _columns: dict[str, np.ndarray]
    _row_names: list[str]

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._columns[key]
        raise KeyError(key)

    @property
    def columns(self) -> dict[str, np.ndarray]:
        return self._columns


class ClmmCondVarLike:
    """Minimal clmm fit carrying fields used by condVar.clmm."""

    def __init__(
        self,
        *,
        gf_list_levels: list[list[str]],
        gf_list_names: list[str],
        gf_assign: np.ndarray,
        st_matrices: list[np.ndarray],
        st_colnames: list[list[str]],
        dims_nretrms: int,
        dims_nlev_re: np.ndarray,
        dims_qi: np.ndarray,
        ranef: np.ndarray,
        cond_var: np.ndarray,
    ):
        self.gfList = gf_list_levels
        self._gf_list_names = list(gf_list_names)
        self._gf_assign = np.asarray(gf_assign, dtype=int).reshape(-1)
        self.ST = st_matrices
        self._st_colnames = st_colnames
        self.dims = {
            "nretrms": int(dims_nretrms),
            "nlev.re": np.asarray(dims_nlev_re, dtype=int).reshape(-1),
            "qi": np.asarray(dims_qi, dtype=int).reshape(-1),
        }
        self.ranef = np.asarray(ranef, dtype=float).reshape(-1)
        self.condVar = np.asarray(cond_var, dtype=float)


def _format_ranef_blocks(
    relist: list[np.ndarray],
    st_colnames: list[list[str]],
    gf_levels: list[list[str]],
    assign: np.ndarray,
    qi: np.ndarray,
    gf_names: list[str],
) -> dict[str, CondVarFrame]:
    """Shared layout from ranef.clmm / condVar.clmm formatRanef."""
    assign = np.asarray(assign, dtype=int).reshape(-1)
    term_mats: list[np.ndarray] = []
    for i, block in enumerate(relist):
        ncol = int(qi[i])
        term_mats.append(np.asarray(block, dtype=float).reshape(-1, ncol, order="F"))

    out: dict[str, CondVarFrame] = {}
    for gf_i, gf_name in enumerate(gf_names, start=1):
        term_indices = [t for t, g in enumerate(assign, start=1) if int(g) == gf_i]
        col_names: list[str] = []
        for ti in term_indices:
            col_names.extend(st_colnames[ti - 1])
        mats = [term_mats[ti - 1] for ti in term_indices]
        mat = np.column_stack(mats) if len(mats) > 1 else mats[0]
        columns = {name: mat[:, j].copy() for j, name in enumerate(col_names)}
        out[gf_name] = CondVarFrame(_columns=columns, _row_names=list(gf_levels[gf_i - 1]))
    return out


def _cond_var_clmm(object: ClmmCondVarLike) -> dict[str, CondVarFrame]:
    dims = object.dims
    nretrms = int(dims["nretrms"])
    nlev_re = np.asarray(dims["nlev.re"], dtype=int).reshape(-1)
    qi = np.asarray(dims["qi"], dtype=int).reshape(-1)
    reind = np.repeat(np.arange(1, nretrms + 1), nlev_re * qi)

    cond_var = np.asarray(object.condVar, dtype=float)
    if cond_var.ndim == 2 and cond_var.shape[1] > 1:
        cond_var = np.diag(cond_var)
    else:
        cond_var = cond_var.reshape(-1)

    cvlist = [cond_var[reind == k] for k in range(1, nretrms + 1)]
    gf_levels = [list(levels) for levels in object.gfList]
    st_colnames = object._st_colnames
    return _format_ranef_blocks(
        cvlist,
        st_colnames,
        gf_levels,
        object._gf_assign,
        qi,
        object._gf_list_names,
    )


def cond_var(object: Any) -> dict[str, CondVarFrame]:
    """Generic condVar; dispatches on clmm-like objects."""
    if isinstance(object, ClmmCondVarLike):
        return _cond_var_clmm(object)
    if hasattr(object, "condVar") and hasattr(object, "gfList") and hasattr(object, "dims"):
        return _cond_var_clmm(object)
    raise TypeError("cond_var requires a clmm-like fit object")


def cond_var_values(result: dict[str, CondVarFrame]) -> np.ndarray:
    """Flatten conditional variances in R list/data.frame order (column-major)."""
    parts: list[np.ndarray] = []
    for name in result:
        frame = result[name]
        for col in frame.columns.values():
            parts.append(np.ravel(col, order="F"))
    return np.concatenate(parts) if parts else np.empty(0, dtype=float)


def clmm_cond_var_like_from_npz(path: str) -> ClmmCondVarLike:
    data = np.load(path, allow_pickle=True)
    gf_levels = [list(x) for x in data["gf_levels"]]
    st_count = int(np.asarray(data["st_count"]).item())
    st_matrices = []
    st_colnames = []
    for i in range(st_count):
        st_matrices.append(np.asarray(data[f"ST_{i}"], dtype=float))
        st_colnames.append([str(x) for x in data[f"ST_colnames_{i}"].tolist()])
    return ClmmCondVarLike(
        gf_list_levels=gf_levels,
        gf_list_names=[str(x) for x in data["gf_names"].tolist()],
        gf_assign=np.asarray(data["assign"], dtype=int),
        st_matrices=st_matrices,
        st_colnames=st_colnames,
        dims_nretrms=int(np.asarray(data["nretrms"]).item()),
        dims_nlev_re=np.asarray(data["nlev_re"], dtype=int),
        dims_qi=np.asarray(data["qi"], dtype=int),
        ranef=np.asarray(data["ranef"], dtype=float),
        cond_var=np.asarray(data["cond_var"], dtype=float),
    )
